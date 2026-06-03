# result_page.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import tushare as ts
from data_utils import get_stock_data
from indicators import compute_all_indicators
from backtest import run_backtest, calculate_metrics, multi_strategy_backtest
from strategies import ma_strategy, rsi_strategy, bollinger_strategy
from plot_charts import plot_equity_curve
from fundamental import get_fundamental_single as get_fundamental, get_value_factors
from plot_utils import plot_candlestick_with_indicators, plot_rsi, plot_macd, plot_kdj
from explain_utils import (
    indicator_glossary, explain_signal, explain_pe, explain_pb,
    signal_historical_performance, explain_main_indicators,
    explain_rsi, explain_macd, explain_kdj
)

def show():
    st.title("📊 MiniQuant 量化分析平台")
    st.markdown("### 2️⃣ 分析结果")

    if st.button("← 返回修改参数"):
        st.session_state.page = 'config'
        st.rerun()

    config = st.session_state.config
    symbol = config['symbol']
    start_date = config['start_date']
    end_date = config['end_date']

    with st.spinner("正在加载数据..."):
        df = get_stock_data(symbol, start_date.strftime('%Y%m%d'), end_date.strftime('%Y%m%d'))
        if df.empty:
            st.error("未获取到数据，请检查股票代码或日期范围")
            return
        df = compute_all_indicators(df)

        # 补充 MACD/KDJ
        if 'MACD' not in df.columns:
            exp12 = df['close'].ewm(span=12, adjust=False).mean()
            exp26 = df['close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = exp12 - exp26
            df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['MACD_hist'] = df['MACD'] - df['MACD_signal']
        if 'K' not in df.columns:
            low_min = df['low'].rolling(9).min()
            high_max = df['high'].rolling(9).max()
            rsv = (df['close'] - low_min) / (high_max - low_min) * 100
            df['K'] = rsv.ewm(span=3, adjust=False).mean()
            df['D'] = df['K'].ewm(span=3, adjust=False).mean()
            df['J'] = 3 * df['K'] - 2 * df['D']

        # 交易日标识
        df['is_trading_day'] = (df['volume'] > 0) & (df['return'].notna())

        # 预计算主策略所需指标
        main_strategy = config['strategy']
        main_params = config['params']
        if main_strategy == "双均线":
            short_ma = main_params['short_ma']
            long_ma = main_params['long_ma']
            if f'MA{short_ma}' not in df.columns:
                df[f'MA{short_ma}'] = df['close'].rolling(short_ma).mean()
            if f'MA{long_ma}' not in df.columns:
                df[f'MA{long_ma}'] = df['close'].rolling(long_ma).mean()
        elif main_strategy == "RSI策略":
            period = main_params['period']
            if f'RSI_{period}' not in df.columns:
                delta = df['close'].diff()
                gain = delta.clip(lower=0)
                loss = -delta.clip(upper=0)
                avg_gain = gain.rolling(period).mean()
                avg_loss = loss.rolling(period).mean()
                rs = avg_gain / avg_loss
                df[f'RSI_{period}'] = 100 - 100 / (1 + rs)
        elif main_strategy == "布林带策略":
            period = main_params['period']
            std_dev = main_params['std_dev']
            mid = df['close'].rolling(period).mean()
            std = df['close'].rolling(period).std()
            df['BB_mid'] = mid
            df['BB_upper'] = mid + std_dev * std
            df['BB_lower'] = mid - std_dev * std

        # 大盘趋势过滤数据准备
        idx_signal = pd.Series(True, index=df.index)
        if config.get('enable_trend_filter', False):
            try:
                pro = ts.pro_api()
                idx_df = pro.index_daily(ts_code='000300.SH',
                                         start_date=start_date.strftime('%Y%m%d'),
                                         end_date=end_date.strftime('%Y%m%d'))
                idx_df['trade_date'] = pd.to_datetime(idx_df['trade_date'])
                idx_df.set_index('trade_date', inplace=True)
                idx_df['MA20'] = idx_df['close'].rolling(20).mean()
                idx_signal = (idx_df['close'] > idx_df['MA20']).reindex(df.index, method='ffill').fillna(True)
            except Exception as e:
                st.warning(f"获取指数数据失败，趋势过滤已禁用: {e}")

        # 生成策略信号
        if main_strategy == "双均线":
            df_strat = ma_strategy(df, main_params['short_ma'], main_params['long_ma'])
        elif main_strategy == "RSI策略":
            df_strat = rsi_strategy(df, main_params['period'], main_params['oversold'], main_params['overbought'])
        else:
            df_strat = bollinger_strategy(df, main_params['period'], main_params['std_dev'])

        # 价值因子开仓检查
        if config.get('enable_value_filter', False):
            with st.spinner("正在获取价值因子数据..."):
                try:
                    value_df = get_value_factors(symbol, start_date.strftime('%Y%m%d'), end_date.strftime('%Y%m%d'))
                    # 对齐到 df 索引
                    value_df = value_df.reindex(df.index, method='ffill')
                    # 构建条件列表
                    conditions = []
                    if config.get('enable_pe', False) and 'PE' in value_df.columns:
                        conditions.append(value_df['PE'] <= config['pe_max'])
                    if config.get('enable_pb', False) and 'PB' in value_df.columns:
                        conditions.append(value_df['PB'] <= config['pb_max'])
                    if config.get('enable_mcap', False) and '市值(亿)' in value_df.columns:
                        conditions.append(value_df['市值(亿)'] >= config['min_mcap'])
                    if config.get('enable_roe', False) and 'ROE' in value_df.columns:
                        conditions.append(value_df['ROE'] >= config['min_roe'])
                    if config.get('enable_gpm', False) and '毛利率' in value_df.columns:
                        conditions.append(value_df['毛利率'] >= config['min_gpm'])
                    if config.get('enable_npm', False) and '净利率' in value_df.columns:
                        conditions.append(value_df['净利率'] >= config['min_npm'])
                    if config.get('enable_debt', False) and '资产负债率' in value_df.columns:
                        conditions.append(value_df['资产负债率'] <= config['max_debt'])
                    if not conditions:
                        st.warning("未启用任何价值因子，跳过过滤")
                    else:
                        if config['value_logic'] == 'AND':
                            value_ok = pd.concat(conditions, axis=1).all(axis=1)
                        else:
                            value_ok = pd.concat(conditions, axis=1).any(axis=1)
                        # 仅对买入信号当天检查
                        buy_signals = (df_strat['signal'] == 1)
                        # 不满足价值条件的买入信号置为0
                        df_strat.loc[buy_signals & ~value_ok, 'signal'] = 0
                        # 重新计算 position（基于修改后的 signal）
                        # 简单循环重建 position
                        position = 0
                        pos_list = []
                        for idx, row in df_strat.iterrows():
                            if row['signal'] == 1:
                                position = 1
                            elif row['signal'] == -1:
                                position = 0
                            pos_list.append(position)
                        df_strat['position'] = pos_list
                        # 重新计算 signal 的 diff（可选，但已经手动处理了，无需）
                except Exception as e:
                    st.warning(f"价值因子数据获取失败，已跳过过滤: {e}")

        # 应用趋势过滤
        if config.get('enable_trend_filter', False):
            df_strat['position'] = df_strat['position'] * idx_signal.astype(int)
            df_strat['signal'] = df_strat['position'].diff()

        # 应用成交量确认
        if config.get('enable_volume_filter', False):
            df['volume_ma20'] = df['volume'].rolling(20).mean()
            volume_ok = df['volume'] > df['volume_ma20'] * 1.5
            buy_signals = (df_strat['signal'] == 1) & ~volume_ok
            df_strat.loc[buy_signals, 'signal'] = 0
            df_strat['position'] = df_strat['position'].where(~buy_signals, 0)
            df_strat['signal'] = df_strat['position'].diff()

        # 动态止损参数
        stop_loss_mult = config.get('stop_loss_atr_mult', None)
        if stop_loss_mult is not None and stop_loss_mult > 0:
            stop_loss_mult = float(stop_loss_mult)
        else:
            stop_loss_mult = None

        # 运行回测
        df_strat = run_backtest(df_strat,
                                commission=config['commission'],
                                slippage=config['slippage'],
                                initial_capital=config['initial_capital'],
                                rebalance_freq=config['rebalance_freq'],
                                stop_loss_atr_mult=stop_loss_mult)

        metrics = calculate_metrics(df_strat)

        # 基本信息
        latest = df.iloc[-1]
        col1, col2, col3 = st.columns(3)
        col1.metric("最新价", f"{latest['close']:.2f}")
        col2.metric("涨跌幅", f"{(latest['close']/df.iloc[-2]['close']-1)*100:.2f}%")
        col3.metric("成交量(手)", f"{latest['volume']:.0f}")

        # 基本面数据（展示用）
        with st.expander("📊 基本面数据（最新一期）", expanded=False):
            with st.spinner("加载中..."):
                fund = get_fundamental(symbol)
                if fund:
                    f1, f2, f3 = st.columns(3)
                    f1.metric("市盈率(PE)", fund.get('PE', '-'))
                    f2.metric("市净率(PB)", fund.get('PB', '-'))
                    f3.metric("市值(亿元)", fund.get('市值(亿)', '-'))
                    st.caption(f"营收: {fund.get('营收(亿)', '-')}亿  净利润: {fund.get('净利润(亿)', '-')}亿  ROE: {fund.get('ROE(%)', '-')}%")
                else:
                    st.info("暂无数据，请检查 Tushare token 或网络")

        # 主图
        st.subheader("价格走势与技术指标")
        fig_main = plot_candlestick_with_indicators(df, config['ma_periods'], config['bb_period'],
                                                    config['bb_std'], config['show_candlestick'])
        st.plotly_chart(fig_main, use_container_width=True)
        with st.expander("📖 主图指标解释（MA5/MA20/MA60/布林带）"):
            explain_main_indicators()

        # 副图
        if config.get('show_rsi'):
            st.subheader("RSI 相对强弱指数")
            fig_rsi = plot_rsi(df, config['rsi_period'], config['rsi_overbought'], config['rsi_oversold'])
            st.plotly_chart(fig_rsi, use_container_width=True)
            with st.expander("📖 RSI 指标详解"):
                explain_rsi()
        if config.get('show_macd'):
            st.subheader("MACD 异同移动平均线")
            fig_macd = plot_macd(df)
            st.plotly_chart(fig_macd, use_container_width=True)
            with st.expander("📖 MACD 指标详解"):
                explain_macd()
        if config.get('show_kdj'):
            st.subheader("KDJ 随机指标")
            fig_kdj = plot_kdj(df)
            st.plotly_chart(fig_kdj, use_container_width=True)
            with st.expander("📖 KDJ 指标详解"):
                explain_kdj()

        # 策略回测绩效
        st.subheader("策略回测")
        with st.expander("⚙️ 当前策略参数详解"):
            if main_strategy == "双均线":
                st.markdown(f"- 短期均线: {main_params['short_ma']}日\n- 长期均线: {main_params['long_ma']}日")
            elif main_strategy == "RSI策略":
                st.markdown(f"- RSI周期: {main_params['period']}\n- 买入阈值: RSI < {main_params['oversold']}\n- 卖出阈值: RSI > {main_params['overbought']}")
            else:
                st.markdown(f"- 布林带周期: {main_params['period']}\n- 标准差倍数: {main_params['std_dev']}")

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("年化收益率", f"{metrics.get('年化收益率（策略）',0)*100:.2f}%")
        col_b.metric("夏普比率", f"{metrics.get('夏普比率',0):.2f}")
        col_c.metric("最大回撤", f"{metrics.get('最大回撤',0)*100:.2f}%")

        # 资金与基准对比
        st.subheader("💰 资金与基准对比")
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("最终策略资产", f"{df_strat['strategy_value'].iloc[-1]:.2f}元")
        col_m2.metric("最终基准资产", f"{df_strat['benchmark_value'].iloc[-1]:.2f}元")
        col_m3.metric("超额收益", f"{df_strat['strategy_value'].iloc[-1] - df_strat['benchmark_value'].iloc[-1]:.2f}元")

        from backtest import calc_outperform_stats
        outperform = calc_outperform_stats(df_strat)
        st.subheader("🏆 跑赢基准统计")
        st.write(f"- 跑赢基准的天数占比: {outperform['跑赢天数占比']:.2%}")
        st.write(f"- 累计超额收益(净值): {outperform['累计超额收益(净值)']:.4f}")
        st.write(f"- 平均日超额收益率: {outperform['平均日超额收益率']:.4%}")

        # 信号解释
        last_signal = df_strat[df_strat['signal'].notna() & (df_strat['signal'] != 0)].iloc[-1] if len(df_strat[df_strat['signal'].notna() & (df_strat['signal'] != 0)]) > 0 else None
        if last_signal is not None:
            explanation = explain_signal(last_signal, main_strategy, main_params)
            if explanation:
                st.info(explanation)

        # 资金曲线图
        fig_curve = plot_equity_curve(df_strat, benchmark_col='benchmark_net', strategy_col='strategy_net')
        st.pyplot(fig_curve)

        # 历史信号统计
        with st.expander("📊 历史信号表现统计", expanded=False):
            stats = signal_historical_performance(df_strat)
            if stats:
                st.write("历史上出现买入信号后的平均收益与胜率：")
                for period, data in stats.items():
                    col1, col2 = st.columns(2)
                    col1.metric(f"{period} 平均收益", f"{data['平均收益']:.2%}")
                    col2.metric(f"{period} 胜率", f"{data['胜率']:.2%}")
            else:
                st.info("无买入信号记录")

        # 多策略对比
        if config.get('enable_compare', False) and len(config.get('compare_strategies', [])) > 0:
            st.subheader("📊 多策略对比")
            compare_configs = []
            for cs in config['compare_strategies']:
                if cs == "双均线":
                    p = config['compare_params'][cs]
                    compare_configs.append({'name': cs, 'strategy_func': ma_strategy, 'params': p})
                elif cs == "RSI策略":
                    p = config['compare_params'][cs]
                    compare_configs.append({'name': cs, 'strategy_func': rsi_strategy, 'params': p})
                else:
                    p = config['compare_params'][cs]
                    compare_configs.append({'name': cs, 'strategy_func': bollinger_strategy, 'params': p})
            results = multi_strategy_backtest(df, compare_configs,
                                              config['commission'], config['slippage'],
                                              config['initial_capital'], config['rebalance_freq'])
            fig_comp = go.Figure()
            for name, res in results.items():
                if res:
                    nav = res['df']['strategy_net']
                    fig_comp.add_trace(go.Scatter(x=nav.index, y=nav, mode='lines', name=name))
            benchmark_nav = (1 + df['return']).cumprod()
            fig_comp.add_trace(go.Scatter(x=benchmark_nav.index, y=benchmark_nav, mode='lines', name='基准', line=dict(dash='dash', color='gray')))
            fig_comp.update_layout(title='多策略资金曲线对比', xaxis_title='日期', yaxis_title='累计净值', hovermode='x unified')
            st.plotly_chart(fig_comp, use_container_width=True)
            comp_data = []
            for name, res in results.items():
                if res:
                    m = res['metrics']
                    comp_data.append({'策略': name,
                                      '年化收益': f"{m.get('年化收益率（策略）',0)*100:.2f}%",
                                      '夏普比率': f"{m.get('夏普比率',0):.2f}",
                                      '最大回撤': f"{m.get('最大回撤',0)*100:.2f}%",
                                      '最终资产': f"{m.get('最终资产(元)',0):.2f}元"})
            if comp_data:
                st.dataframe(pd.DataFrame(comp_data), use_container_width=True)

        # 热力图
        if config.get('enable_heatmap', False):
            st.subheader("🔥 双均线夏普热力图")
            with st.spinner("网格搜索中，请稍候..."):
                hm_short = config['hm_short']
                hm_long = config['hm_long']
                hm_step = config['hm_step']
                from backtest import grid_search_ma
                short_vals, long_vals, sharpe_mat = grid_search_ma(df, hm_short, hm_long, step=hm_step,
                                                                   commission=config['commission'], slippage=config['slippage'],
                                                                   initial_capital=config['initial_capital'], rebalance_freq=config['rebalance_freq'])
            fig_heat = go.Figure(data=go.Heatmap(x=long_vals, y=short_vals, z=sharpe_mat, colorscale='RdYlGn', zmid=0,
                                                 hovertemplate='短期:%{y}<br>长期:%{x}<br>夏普:%{z:.2f}<extra></extra>'))
            fig_heat.update_layout(title='双均线夏普比率热力图', xaxis_title='长期均线', yaxis_title='短期均线')
            st.plotly_chart(fig_heat, use_container_width=True)

        # 单日数据查看器
        st.subheader("📅 单日数据详情")
        col_date, col_btn = st.columns([3,1])
        with col_date:
            sel_date = st.date_input("选择日期", value=df.index[-1], min_value=df.index.min(), max_value=df.index.max())
        with col_btn:
            if st.button("查看详情"):
                if sel_date in df.index:
                    row = df.loc[sel_date]
                    if not row['is_trading_day']:
                        st.warning(f"⚠️ {sel_date} 为非交易日，数据为前值填充")
                    st.write(f"开盘:{row['open']:.2f}  最高:{row['high']:.2f}  最低:{row['low']:.2f}  收盘:{row['close']:.2f}")
                    st.write(f"成交量:{row['volume']:.0f}手  涨跌幅:{row['return']*100:.2f}%" if pd.notna(row['return']) else "涨跌幅:-")
                else:
                    st.error("日期不在数据范围内")

        # 最近20日数据表格
        with st.expander("📋 查看最近20日原始数据"):
            st.dataframe(df[['open','high','low','close','volume','return','is_trading_day']].tail(20).style.format({
                'open':'{:.2f}','high':'{:.2f}','low':'{:.2f}','close':'{:.2f}','volume':'{:.0f}','return':'{:.4%}'
            }))

        st.success("分析完成！")