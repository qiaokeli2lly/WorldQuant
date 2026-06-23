import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from data_utils import get_stock_data
from indicators import compute_all_indicators
from backtest import run_backtest, calculate_metrics, multi_strategy_backtest, grid_search_ma
from strategies import ma_strategy, rsi_strategy, bollinger_strategy
from plot_charts import plot_equity_curve
from fundamental import get_fundamental
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

        # 动态计算策略所需的指标（避免因参数超出预定义范围而报错）
        if config['strategy'] == "双均线":
            short_ma = config['params']['short_ma']
            long_ma = config['params']['long_ma']
            if f'MA{short_ma}' not in df.columns:
                df[f'MA{short_ma}'] = df['close'].rolling(short_ma).mean()
            if f'MA{long_ma}' not in df.columns:
                df[f'MA{long_ma}'] = df['close'].rolling(long_ma).mean()
        elif config['strategy'] == "RSI策略":
            period = config['params']['period']
            if f'RSI_{period}' not in df.columns:
                delta = df['close'].diff()
                gain = delta.clip(lower=0)
                loss = -delta.clip(upper=0)
                avg_gain = gain.rolling(period).mean()
                avg_loss = loss.rolling(period).mean()
                rs = avg_gain / avg_loss
                df[f'RSI_{period}'] = 100 - 100 / (1 + rs)
        elif config['strategy'] == "布林带策略":
            period = config['params']['period']
            std_dev = config['params']['std_dev']
            mid = df['close'].rolling(period).mean()
            std = df['close'].rolling(period).std()
            df['BB_mid'] = mid
            df['BB_upper'] = mid + std_dev * std
            df['BB_lower'] = mid - std_dev * std

        df['is_trading_day'] = (df['volume'] > 0) & (df['return'].notna())

        # 基本信息
        latest = df.iloc[-1]
        col1, col2, col3 = st.columns(3)
        col1.metric("最新价", f"{latest['close']:.2f}")
        col2.metric("涨跌幅", f"{(latest['close']/df.iloc[-2]['close']-1)*100:.2f}%")
        col3.metric("成交量(手)", f"{latest['volume']:.0f}")

        # 基本面数据
        with st.expander("📊 基本面数据（PE/PB/市值）", expanded=False):
            try:
                fund = get_fundamental(symbol)
                if fund:
                    f1, f2, f3 = st.columns(3)
                    f1.metric("市盈率(PE)", fund.get('PE', '-'))
                    f2.metric("市净率(PB)", fund.get('PB', '-'))
                    f3.metric("市值(亿元)", fund.get('市值(亿)', '-'))
                    st.markdown("---")
                    st.caption("📖 **白话解读**")
                    pe = fund.get('PE')
                    pb = fund.get('PB')
                    if pe is not None:
                        st.write(f"- 市盈率: {explain_pe(pe)}")
                    if pb is not None:
                        st.write(f"- 市净率: {explain_pb(pb)}")
                else:
                    st.info("暂无数据，请检查 Tushare token 或网络")
            except Exception as e:
                st.warning(f"获取失败: {e}")

        # 主图
        st.subheader("价格走势与技术指标")
        fig_main = plot_candlestick_with_indicators(df, config['ma_periods'], config['bb_period'],
                                                    config['bb_std'], config['show_candlestick'])
        st.plotly_chart(fig_main, use_container_width=True)
        with st.expander("📖 主图指标解释（MA5/MA20/MA60/布林带）"):
            explain_main_indicators()

        # 副图指标
        if config['show_rsi']:
            st.subheader("RSI 相对强弱指数")
            fig_rsi = plot_rsi(df, config['rsi_period'], config['rsi_overbought'], config['rsi_oversold'])
            st.plotly_chart(fig_rsi, use_container_width=True)
            with st.expander("📖 RSI 指标详解"):
                explain_rsi()

        if config['show_macd']:
            st.subheader("MACD 异同移动平均线")
            fig_macd = plot_macd(df)
            st.plotly_chart(fig_macd, use_container_width=True)
            with st.expander("📖 MACD 指标详解"):
                explain_macd()

        if config['show_kdj']:
            st.subheader("KDJ 随机指标")
            fig_kdj = plot_kdj(df)
            st.plotly_chart(fig_kdj, use_container_width=True)
            with st.expander("📖 KDJ 指标详解"):
                explain_kdj()

        # 策略回测
        st.subheader("策略回测")
        strategy = config['strategy']
        params = config['params']

        # 显示当前策略参数详解
        with st.expander("⚙️ 当前策略参数详解"):
            if strategy == "双均线":
                st.markdown(f"- 短期均线: {params['short_ma']}日")
                st.markdown(f"- 长期均线: {params['long_ma']}日")
                st.markdown("**解释**: 当短线上穿长线时买入，下穿时卖出。")
            elif strategy == "RSI策略":
                st.markdown(f"- RSI周期: {params['period']}日")
                st.markdown(f"- 买入阈值: RSI < {params['oversold']}")
                st.markdown(f"- 卖出阈值: RSI > {params['overbought']}")
                st.markdown("**解释**: RSI低于超卖线买入，高于超买线卖出。")
            else:
                st.markdown(f"- 布林带周期: {params['period']}日")
                st.markdown(f"- 标准差倍数: {params['std_dev']}")
                st.markdown("**解释**: 价格触及下轨买入，触及上轨卖出。")

        if strategy == "双均线":
            df_strat = ma_strategy(df, params['short_ma'], params['long_ma'])
        elif strategy == "RSI策略":
            df_strat = rsi_strategy(df, params['period'], params['oversold'], params['overbought'])
        else:
            df_strat = bollinger_strategy(df, params['period'], params['std_dev'])

        df_strat = run_backtest(df_strat, config['commission'], config['slippage'])
        metrics = calculate_metrics(df_strat)
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("年化收益率", f"{metrics.get('年化收益率（策略）',0)*100:.2f}%")
        col_b.metric("夏普比率", f"{metrics.get('夏普比率',0):.2f}")
        col_c.metric("最大回撤", f"{metrics.get('最大回撤',0)*100:.2f}%")

        # 信号解释器
        last_signal = df_strat[df_strat['signal'].notna() & (df_strat['signal'] != 0)].iloc[-1] if len(df_strat[df_strat['signal'].notna() & (df_strat['signal'] != 0)]) > 0 else None
        if last_signal is not None:
            explanation = explain_signal(last_signal, strategy, params)
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
        if config['enable_compare'] and len(config['compare_strategies']) > 0:
            st.subheader("📊 多策略资金曲线对比")
            configs = []
            if "双均线" in config['compare_strategies']:
                configs.append({'name':'双均线', 'strategy_func':ma_strategy, 'params':{'short_ma':5, 'long_ma':20}})
            if "RSI策略" in config['compare_strategies']:
                configs.append({'name':'RSI策略', 'strategy_func':rsi_strategy, 'params':{'period':14, 'oversold':30, 'overbought':70}})
            if "布林带策略" in config['compare_strategies']:
                configs.append({'name':'布林带策略', 'strategy_func':bollinger_strategy, 'params':{'period':20, 'std_dev':2.0}})
            results = multi_strategy_backtest(df, configs, config['commission'], config['slippage'])
            fig_comp = go.Figure()
            for name, res in results.items():
                if res:
                    nav = res['df']['strategy_net']
                    fig_comp.add_trace(go.Scatter(x=nav.index, y=nav, mode='lines', name=name))
            fig_comp.update_layout(title='策略净值对比', xaxis_title='日期', yaxis_title='累计净值', hovermode='x unified')
            st.plotly_chart(fig_comp, use_container_width=True)
            comp_data = []
            for name, res in results.items():
                if res:
                    m = res['metrics']
                    comp_data.append({'策略':name, '年化收益':f"{m.get('年化收益率（策略）',0)*100:.2f}%",
                                      '夏普':f"{m.get('夏普比率',0):.2f}", '最大回撤':f"{m.get('最大回撤',0)*100:.2f}%"})
            if comp_data:
                st.dataframe(pd.DataFrame(comp_data), use_container_width=True)

        # 热力图
        if config['enable_heatmap']:
            st.subheader("🔥 双均线夏普热力图")
            with st.spinner("网格搜索中，请稍候..."):
                hm_short = config['hm_short']
                hm_long = config['hm_long']
                hm_step = config['hm_step']
                short_vals, long_vals, sharpe_mat = grid_search_ma(df, hm_short, hm_long, step=hm_step,
                                                                   commission=config['commission'], slippage=config['slippage'])
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