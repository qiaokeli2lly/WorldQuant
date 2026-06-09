# pages/result_page.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import tushare as ts
from data.stock_data import get_stock_data
from data.fundamental import get_fundamental_single as get_fundamental, get_value_factors
from utils.indicators import compute_all_indicators
from backtest.single_backtest import run_backtest, multi_strategy_backtest, grid_search_ma
from backtest.metrics import calculate_metrics, calc_outperform_stats
from strategies.ma_strategy import ma_strategy
from strategies.rsi_strategy import rsi_strategy
from strategies.bollinger_strategy import bollinger_strategy
from visualization.plot_charts import plot_equity_curve
from visualization.plot_utils import plot_candlestick_with_indicators, plot_rsi, plot_macd, plot_kdj
from visualization.explain_utils import (
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

        # 确保 MACD 存在
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
        df['is_trading_day'] = (df['volume'] > 0) & (df['return'].notna())

        # 获取价值因子数据
        try:
            value_df = get_value_factors(symbol, start_date.strftime('%Y%m%d'), end_date.strftime('%Y%m%d'))
            if value_df is not None and not value_df.empty:
                latest_value = value_df.iloc[-1].to_dict()
                latest_value = {k: v for k, v in latest_value.items() if pd.notna(v)}
                # 保存到 session_state 供 config_page 使用
                st.session_state.latest_fundamental = latest_value
            else:
                latest_value = None
                value_df = None
        except Exception as e:
            st.warning(f"获取价值因子数据失败: {e}")
            value_df = None
            latest_value = None

        # 策略信号生成与过滤
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
            except:
                pass

        if main_strategy == "双均线":
            df_strat = ma_strategy(df, main_params['short_ma'], main_params['long_ma'])
        elif main_strategy == "RSI策略":
            df_strat = rsi_strategy(df, main_params['period'], main_params['oversold'], main_params['overbought'])
        else:
            df_strat = bollinger_strategy(df, main_params['period'], main_params['std_dev'])

        if config.get('enable_value_filter', False) and value_df is not None:
            try:
                value_df_aligned = value_df.reindex(df.index, method='ffill')
                conditions = []
                if config.get('enable_pe', False) and config.get('pe_max') is not None and 'PE' in value_df_aligned.columns:
                    conditions.append(value_df_aligned['PE'] <= config['pe_max'])
                if config.get('enable_pb', False) and config.get('pb_max') is not None and 'PB' in value_df_aligned.columns:
                    conditions.append(value_df_aligned['PB'] <= config['pb_max'])
                if config.get('enable_mcap', False) and config.get('min_mcap') is not None and '市值(亿)' in value_df_aligned.columns:
                    conditions.append(value_df_aligned['市值(亿)'] >= config['min_mcap'])
                if config.get('enable_roe', False) and config.get('min_roe') is not None and 'ROE' in value_df_aligned.columns:
                    conditions.append(value_df_aligned['ROE'] >= config['min_roe'])
                if config.get('enable_gpm', False) and config.get('min_gpm') is not None and '毛利率' in value_df_aligned.columns:
                    conditions.append(value_df_aligned['毛利率'] >= config['min_gpm'])
                if config.get('enable_npm', False) and config.get('min_npm') is not None and '净利率' in value_df_aligned.columns:
                    conditions.append(value_df_aligned['净利率'] >= config['min_npm'])
                if config.get('enable_debt', False) and config.get('max_debt') is not None and '资产负债率' in value_df_aligned.columns:
                    conditions.append(value_df_aligned['资产负债率'] <= config['max_debt'])
                if conditions:
                    if config['value_logic'] == 'AND':
                        value_ok = pd.concat(conditions, axis=1).all(axis=1)
                    else:
                        value_ok = pd.concat(conditions, axis=1).any(axis=1)
                    buy_signals = (df_strat['signal'] == 1)
                    df_strat.loc[buy_signals & ~value_ok, 'signal'] = 0
                    position = 0
                    pos_list = []
                    for idx, row in df_strat.iterrows():
                        if row['signal'] == 1:
                            position = 1
                        elif row['signal'] == -1:
                            position = 0
                        pos_list.append(position)
                    df_strat['position'] = pos_list
            except Exception as e:
                st.warning(f"价值因子过滤失败: {e}")

        if config.get('enable_trend_filter', False):
            df_strat['position'] = df_strat['position'] * idx_signal.astype(int)
            df_strat['signal'] = df_strat['position'].diff()
        if config.get('enable_volume_filter', False):
            df['volume_ma20'] = df['volume'].rolling(20).mean()
            volume_ok = df['volume'] > df['volume_ma20'] * 1.5
            buy_signals = (df_strat['signal'] == 1) & ~volume_ok
            df_strat.loc[buy_signals, 'signal'] = 0
            df_strat['position'] = df_strat['position'].where(~buy_signals, 0)
            df_strat['signal'] = df_strat['position'].diff()

        stop_loss_mult = config.get('stop_loss_atr_mult', None)
        if stop_loss_mult is not None and stop_loss_mult > 0:
            stop_loss_mult = float(stop_loss_mult)
        else:
            stop_loss_mult = None

        df_strat = run_backtest(df_strat,
                                commission=config['commission'],
                                slippage=config['slippage'],
                                initial_capital=config['initial_capital'],
                                rebalance_freq=config['rebalance_freq'],
                                stop_loss_atr_mult=stop_loss_mult)
        metrics = calculate_metrics(df_strat)

        # ---------- 顶部数据概览 ----------
        latest = df.iloc[-1]
        col1, col2, col3 = st.columns(3)
        col1.metric("最新价", f"{latest['close']:.2f}")
        col2.metric("涨跌幅", f"{(latest['close']/df.iloc[-2]['close']-1)*100:.2f}%")
        col3.metric("成交量(手)", f"{latest['volume']:.0f}")

        # ---------- 策略绩效与诊断 ----------
        st.subheader("📊 策略回测绩效")
        col_a, col_b, col_c = st.columns(3)
        ann_ret = metrics.get('年化收益率（策略）', 0)
        sharpe = metrics.get('夏普比率', 0)
        max_dd = metrics.get('最大回撤', 0)
        col_a.metric("年化收益率（策略）", f"{ann_ret*100:.2f}%")
        col_b.metric("夏普比率", f"{sharpe:.2f}")
        col_c.metric("最大回撤", f"{max_dd*100:.2f}%")
        bench_ret = metrics.get('年化收益率（基准）', 0)
        st.caption(f"📈 基准（沪深300）年化收益率：{bench_ret*100:.2f}%")

        # 指标好坏判断
        ret_judge = "优秀 👍" if ann_ret > 0.15 else ("良好 ✅" if ann_ret > 0.05 else ("一般 💡" if ann_ret > 0 else "亏损 ⚠️"))
        sharpe_judge = "优秀 👍" if sharpe > 1.5 else ("良好 ✅" if sharpe > 0.8 else "偏低 ⚠️")
        dd_judge = "风险小 👍" if max_dd > -0.1 else ("中等 ✅" if max_dd > -0.2 else "回撤较大 ⚠️")
        st.info(f"年化收益率 {ret_judge} | 夏普比率 {sharpe_judge} | 最大回撤 {dd_judge}")

        # 策略诊断
        trade_cnt = metrics.get('交易次数', 0)
        if trade_cnt == 0:
            reasons = []
            if config.get('enable_value_filter'):
                reasons.append("价值因子过滤条件可能过于严格，导致所有买入信号都被拦截")
            if config.get('enable_trend_filter'):
                reasons.append("大盘趋势过滤开启，回测期内沪深300长期处于下跌趋势，策略空仓")
            if config.get('enable_volume_filter'):
                reasons.append("成交量确认开启，买入信号未满足放量条件")
            if not reasons:
                reasons.append("策略本身未产生信号（可能参数设置不当或数据问题）")
            st.error(f"⚠️ 策略在回测期内未产生任何交易。可能原因：{'；'.join(reasons)}。建议调整过滤条件或策略参数。")
        elif trade_cnt < 5:
            st.warning(f"💡 交易次数较少（仅{trade_cnt}次），策略可能过于保守，请检查过滤条件。")

        # 跑输基准诊断
        if ann_ret < bench_ret:
            st.warning(f"📉 策略年化收益率 ({ann_ret*100:.2f}%) 跑输基准 ({bench_ret*100:.2f}%)。可能原因：")
            if main_strategy == "RSI策略":
                st.markdown("- RSI策略在**单边行情中容易过早卖出**，如果该股票回测期内涨幅较大，策略可能踏空。建议尝试双均线。")
            elif main_strategy == "布林带策略":
                st.markdown("- 布林带策略在**趋势突破时可能反复止损**，建议检查股价是否突破轨道后持续单边运行。")
            else:
                st.markdown("- 双均线策略在**震荡市中可能频繁假信号**，产生亏损。可考虑拉长均线周期减少噪音。")
            st.markdown("- 检查手续费和滑点设置是否过高，或调仓频率过高导致交易成本侵蚀利润。")
        else:
            st.success(f"🎉 策略跑赢基准 {ann_ret*100 - bench_ret*100:.2f}%，择时有效！")

        # 资金与基准对比
        st.subheader("💰 资金与基准对比")
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("最终策略资产", f"{df_strat['strategy_value'].iloc[-1]:.2f}元")
        col_m2.metric("最终基准资产", f"{df_strat['benchmark_value'].iloc[-1]:.2f}元")
        col_m3.metric("超额收益", f"{df_strat['strategy_value'].iloc[-1] - df_strat['benchmark_value'].iloc[-1]:.2f}元")

        outperform = calc_outperform_stats(df_strat)
        st.subheader("🏆 跑赢基准统计")
        st.write(f"- 跑赢基准的天数占比: {outperform['跑赢天数占比']:.2%}")
        st.write(f"- 累计超额收益(净值): {outperform['累计超额收益(净值)']:.4f}")
        st.write(f"- 平均日超额收益率: {outperform['平均日超额收益率']:.4%}")

        # 最新信号解释
        last_signal = df_strat[df_strat['signal'].notna() & (df_strat['signal'] != 0)].iloc[-1] if len(df_strat[df_strat['signal'].notna() & (df_strat['signal'] != 0)]) > 0 else None
        if last_signal is not None:
            explanation = explain_signal(last_signal, main_strategy, main_params)
            if explanation:
                st.info(explanation)

        # 资金曲线
        fig_curve = plot_equity_curve(df_strat, benchmark_col='benchmark_net', strategy_col='strategy_net')
        st.pyplot(fig_curve)

        # 历史信号表现
        with st.expander("📊 历史信号表现统计", expanded=False):
            stats = signal_historical_performance(df_strat)
            if stats:
                for period, data in stats.items():
                    col1, col2 = st.columns(2)
                    col1.metric(f"{period} 平均收益", f"{data['平均收益']:.2%}")
                    col2.metric(f"{period} 胜率", f"{data['胜率']:.2%}")
            else:
                st.info("无买入信号记录")

        # 技术指标图表与当前状态解释
        st.subheader("价格走势与技术指标")
        fig_main = plot_candlestick_with_indicators(df, config['ma_periods'], config['bb_period'],
                                                    config['bb_std'], config['show_candlestick'])
        st.plotly_chart(fig_main, width='stretch')
        with st.expander("📖 主图指标解释"):
            explain_main_indicators()

        if config.get('show_rsi'):
            st.subheader("RSI")
            fig_rsi = plot_rsi(df, config['rsi_period'], config['rsi_overbought'], config['rsi_oversold'])
            st.plotly_chart(fig_rsi, width='stretch')
            # 当前RSI解释
            rsi_col = f"RSI_{config['rsi_period']}"
            if rsi_col in df.columns:
                last_rsi = df[rsi_col].iloc[-1]
                if last_rsi > config['rsi_overbought']:
                    st.warning(f"📊 当前RSI: {last_rsi:.1f}，处于**超买区**（>{config['rsi_overbought']}），短线可能回调。")
                elif last_rsi < config['rsi_oversold']:
                    st.warning(f"📊 当前RSI: {last_rsi:.1f}，处于**超卖区**（<{config['rsi_oversold']}），短线可能反弹。")
                else:
                    st.info(f"📊 当前RSI: {last_rsi:.1f}，处于**中性区间**。")

        if config.get('show_macd'):
            st.subheader("MACD")
            fig_macd = plot_macd(df)
            st.plotly_chart(fig_macd, width='stretch')
            if 'MACD' in df.columns and 'MACD_signal' in df.columns:
                last_macd = df['MACD'].iloc[-1]
                last_signal_line = df['MACD_signal'].iloc[-1]
                if last_macd > last_signal_line:
                    st.info("📊 MACD 处于**金叉状态**（快线在慢线上方），短期看涨。")
                else:
                    st.warning("📊 MACD 处于**死叉状态**（快线在慢线下方），短期看跌。")

        if config.get('show_kdj'):
            st.subheader("KDJ")
            fig_kdj = plot_kdj(df)
            st.plotly_chart(fig_kdj, width='stretch')
            if 'K' in df.columns:
                last_k = df['K'].iloc[-1]
                if last_k > 80:
                    st.warning(f"📊 KDJ 的K值: {last_k:.1f}，处于**超买区**，短线可能回调。")
                elif last_k < 20:
                    st.warning(f"📊 KDJ 的K值: {last_k:.1f}，处于**超卖区**，短线可能反弹。")
                else:
                    st.info(f"📊 KDJ 的K值: {last_k:.1f}，处于**中性区间**。")

        # 策略原理与适用场景
        with st.expander("📖 策略原理与适用场景", expanded=False):
            if main_strategy == "双均线":
                st.markdown("""
                **双均线策略**  
                - **策略行为**：当短期均线上穿长期均线（金叉）时买入，下穿（死叉）时卖出。  
                - **适用场景**：股价呈现单边上涨或下跌趋势的行情。  
                - **失效场景**：在横盘震荡或无明显趋势的市场中，金叉死叉信号频繁出现，容易导致反复止损，策略失效。  
                - **通俗解释**：可以想象为“当短期价格趋势超过长期价格趋势时买入，反之卖出”。适合有明显上升或下降通道的股票。
                """)
            elif main_strategy == "RSI策略":
                st.markdown("""
                **RSI策略**  
                - **策略行为**：当相对强弱指数（RSI）低于超卖线时买入（预期反弹），高于超买线时卖出（预期回调）。  
                - **适用场景**：股价在一定的区间内来回震荡，没有明显单边趋势。  
                - **失效场景**：在强烈的单边趋势市场中，RSI可能长时间处于超买或超卖区域，价格不回头，导致策略过早卖出或错过主升浪，从而跑输基准。  
                - **通俗解释**：好比温度计，太高了（>70）可能热过头会降温，太低了（<30）可能冷过头会反弹。适合在一个区间内波动的股票。
                """)
            else:
                st.markdown("""
                **布林带策略**  
                - **策略行为**：当股价触及下轨时买入（超卖反弹），触及上轨时卖出（超买回落）。  
                - **适用场景**：股价在布林带上下轨之间规律震荡，没有强势突破。  
                - **失效场景**：当股价出现趋势性突破（上涨突破上轨或下跌突破下轨）时，价格可能持续沿着一个方向运行，导致策略反复止损，失效。  
                - **通俗解释**：股价通常在上下两条轨道之间运行，碰到下轨可能弹回来，碰到上轨可能掉下去。适合有明确波动区间的股票。
                """)

        # 因子数据表格
        with st.expander("🧮 当前使用的因子数据（最新一期）", expanded=False):
            if value_df is not None and not value_df.empty:
                latest_row = value_df.iloc[-1]
                factor_display = []
                for col in ['PE', 'PB', '市值(亿)', 'ROE', '毛利率', '净利率', '资产负债率']:
                    if col in latest_row.index and pd.notna(latest_row[col]):
                        value = latest_row[col]
                        value_str = f"{value:.2f}" if isinstance(value, (int, float)) else str(value)
                        if col == '市值(亿)':
                            factor_display.append(('总市值(亿元)', value_str))
                        elif col == 'ROE':
                            factor_display.append(('ROE(%)', value_str))
                        elif col == '毛利率':
                            factor_display.append(('毛利率(%)', value_str))
                        elif col == '净利率':
                            factor_display.append(('净利率(%)', value_str))
                        elif col == '资产负债率':
                            factor_display.append(('资产负债率(%)', value_str))
                        else:
                            factor_display.append((col, value_str))
                fund = get_fundamental(symbol)
                if fund:
                    if fund.get('营收(亿)'):
                        factor_display.append(('营收(亿元)', str(fund.get('营收(亿)'))))
                    if fund.get('净利润(亿)'):
                        factor_display.append(('净利润(亿元)', str(fund.get('净利润(亿)'))))
                if factor_display:
                    df_factors = pd.DataFrame(factor_display, columns=['因子', '最新值'])
                    st.dataframe(df_factors, width='stretch')
                else:
                    st.info("暂无因子数据（可能数据源未返回）")
            else:
                st.info("无法获取价值因子数据")

        with st.expander("📊 基本面数据（最新一期）", expanded=False):
            fund = get_fundamental(symbol)
            if fund:
                f1, f2, f3 = st.columns(3)
                f1.metric("市盈率(PE)", fund.get('PE', '-'))
                f2.metric("市净率(PB)", fund.get('PB', '-'))
                f3.metric("市值(亿元)", fund.get('市值(亿)', '-'))
                st.caption(f"营收: {fund.get('营收(亿)', '-')}亿  净利润: {fund.get('净利润(亿)', '-')}亿  ROE: {fund.get('ROE(%)', '-')}%")
            else:
                st.info("暂无数据")

        with st.expander("📈 季度财务指标趋势（ROE、毛利率、净利率、资产负债率）", expanded=False):
            if value_df is not None and not value_df.empty:
                quarterly = value_df.resample('QE').last()
                fig_q = go.Figure()
                for col in ['ROE', '毛利率', '净利率', '资产负债率']:
                    if col in quarterly.columns:
                        fig_q.add_trace(go.Scatter(x=quarterly.index, y=quarterly[col], mode='lines+markers', name=col))
                fig_q.update_layout(title='季度财务指标历史', xaxis_title='日期', yaxis_title='%', height=400)
                st.plotly_chart(fig_q, width='stretch')
            else:
                st.info("暂无季度因子数据")

        # 多策略对比
        if config.get('enable_compare', False) and len(config.get('compare_strategies', [])) > 0:
            st.subheader("📊 多策略对比")
            compare_configs = []
            for cs in config['compare_strategies']:
                p = config['compare_params'][cs]
                if cs == "双均线":
                    compare_configs.append({'name': cs, 'strategy_func': ma_strategy, 'params': p})
                elif cs == "RSI策略":
                    compare_configs.append({'name': cs, 'strategy_func': rsi_strategy, 'params': p})
                else:
                    compare_configs.append({'name': cs, 'strategy_func': bollinger_strategy, 'params': p})
            results = multi_strategy_backtest(df, compare_configs, config['commission'], config['slippage'],
                                              config['initial_capital'], config['rebalance_freq'])
            fig_comp = go.Figure()
            for name, res in results.items():
                if res:
                    nav = res['df']['strategy_net']
                    fig_comp.add_trace(go.Scatter(x=nav.index, y=nav, mode='lines', name=name))
            benchmark_nav = (1 + df['return']).cumprod()
            fig_comp.add_trace(go.Scatter(x=benchmark_nav.index, y=benchmark_nav, mode='lines', name='基准', line=dict(dash='dash', color='gray')))
            st.plotly_chart(fig_comp, width='stretch')
            comp_data = []
            for name, res in results.items():
                if res:
                    m = res['metrics']
                    comp_data.append({'策略': name, '年化收益': f"{m.get('年化收益率（策略）',0)*100:.2f}%",
                                      '夏普比率': f"{m.get('夏普比率',0):.2f}", '最大回撤': f"{m.get('最大回撤',0)*100:.2f}%"})
            if comp_data:
                st.dataframe(pd.DataFrame(comp_data), width='stretch')

        # 热力图
        if config.get('enable_heatmap', False):
            st.subheader("🔥 双均线夏普热力图")
            with st.spinner("网格搜索中..."):
                short_vals, long_vals, sharpe_mat = grid_search_ma(df, config['hm_short'], config['hm_long'], step=config['hm_step'],
                                                                   commission=config['commission'], slippage=config['slippage'],
                                                                   initial_capital=config['initial_capital'], rebalance_freq=config['rebalance_freq'])
            fig_heat = go.Figure(data=go.Heatmap(x=long_vals, y=short_vals, z=sharpe_mat, colorscale='RdYlGn', zmid=0))
            st.plotly_chart(fig_heat, width='stretch')

        # 单日数据详情
        st.subheader("📅 单日数据详情")
        sel_date = st.date_input("选择日期", value=df.index[-1], min_value=df.index.min(), max_value=df.index.max())
        if st.button("查看详情"):
            if sel_date in df.index:
                row = df.loc[sel_date]
                if not row['is_trading_day']:
                    st.warning(f"⚠️ {sel_date} 为非交易日")
                st.write(f"开盘:{row['open']:.2f}  最高:{row['high']:.2f}  最低:{row['low']:.2f}  收盘:{row['close']:.2f}")
                st.write(f"成交量:{row['volume']:.0f}手  涨跌幅:{row['return']*100:.2f}%")
            else:
                st.error("日期不在范围内")

        with st.expander("📋 查看最近20日原始数据"):
            st.dataframe(df[['open','high','low','close','volume','return','is_trading_day']].tail(20).style.format({
                'open':'{:.2f}','high':'{:.2f}','low':'{:.2f}','close':'{:.2f}','volume':'{:.0f}','return':'{:.4%}'
            }), width='stretch')

        st.success("分析完成！")