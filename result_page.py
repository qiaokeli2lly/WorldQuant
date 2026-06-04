import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import tushare as ts
from data_utils import get_stock_data
from indicators import compute_all_indicators
from backtest import run_backtest, calculate_metrics, multi_strategy_backtest, calc_outperform_stats, grid_search_ma
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

        try:
            value_df = get_value_factors(symbol, start_date.strftime('%Y%m%d'), end_date.strftime('%Y%m%d'))
            if value_df is not None and not value_df.empty:
                latest_value = value_df.iloc[-1].to_dict()
                latest_value = {k: v for k, v in latest_value.items() if pd.notna(v)}
            else:
                latest_value = None
                value_df = None
        except Exception as e:
            st.warning(f"获取价值因子数据失败: {e}")
            value_df = None
            latest_value = None

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

        latest = df.iloc[-1]
        col1, col2, col3 = st.columns(3)
        col1.metric("最新价", f"{latest['close']:.2f}")
        col2.metric("涨跌幅", f"{(latest['close']/df.iloc[-2]['close']-1)*100:.2f}%")
        col3.metric("成交量(手)", f"{latest['volume']:.0f}")

        # ========== 因子数据表格（已修复 Arrow 兼容性）==========
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
                quarterly = value_df.resample('QE').last()  # 修改为 'QE'
                fig_q = go.Figure()
                for col in ['ROE', '毛利率', '净利率', '资产负债率']:
                    if col in quarterly.columns:
                        fig_q.add_trace(go.Scatter(x=quarterly.index, y=quarterly[col], mode='lines+markers', name=col))
                fig_q.update_layout(title='季度财务指标历史', xaxis_title='日期', yaxis_title='%', height=400)
                st.plotly_chart(fig_q, width='stretch')
            else:
                st.info("暂无季度因子数据")

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
        if config.get('show_macd'):
            st.subheader("MACD")
            fig_macd = plot_macd(df)
            st.plotly_chart(fig_macd, width='stretch')
        if config.get('show_kdj'):
            st.subheader("KDJ")
            fig_kdj = plot_kdj(df)
            st.plotly_chart(fig_kdj, width='stretch')

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

        st.subheader("🧠 策略诊断与股票特性分析")
        if len(df) > 50:
            volatility = df['return'].std() * np.sqrt(252)
            if 'MA20' in df.columns:
                trend_strength = (df['close'] - df['MA20']).abs().mean() / df['close'].mean()
            else:
                trend_strength = 0.1
            strategy_ret = metrics.get('年化收益率（策略）', 0)
            benchmark_ret = metrics.get('年化收益率（基准）', 0)
            if strategy_ret > benchmark_ret:
                perf = "跑赢基准"
            elif strategy_ret > 0:
                perf = "正收益但未跑赢基准"
            else:
                perf = "亏损"

            if main_strategy == "双均线":
                if perf == "亏损":
                    advice = f"""
**📉 双均线策略亏损**  
策略年化收益率 {strategy_ret*100:.2f}%，基准年化收益率 {benchmark_ret*100:.2f}%。  
该股票年化波动率 {volatility:.2%}，趋势强度 {trend_strength:.3f}。双均线作为趋势跟踪策略，在震荡或无趋势的市场中容易产生亏损。  
**可尝试的调整**：延长均线周期以过滤噪音，或结合大盘趋势过滤，或改用RSI等适合震荡的策略。  
"""
                elif perf == "正收益但未跑赢基准":
                    advice = f"""
**📈 双均线策略盈利但未跑赢基准**  
策略年化收益率 {strategy_ret*100:.2f}%，基准年化收益率 {benchmark_ret*100:.2f}%。  
该股票波动率 {volatility:.2%}，有一定趋势但不够强劲。策略取得了正收益，但涨幅低于简单持有，可能因交易成本或信号滞后。  
**可尝试的调整**：适当缩短均线周期提高灵敏度，降低手续费假设，或在强势行情中减少仓位。  
"""
                else:
                    advice = f"""
**🚀 双均线策略跑赢基准**  
策略年化收益率 {strategy_ret*100:.2f}%，基准年化收益率 {benchmark_ret*100:.2f}%。  
该股票趋势明显（趋势强度 {trend_strength:.3f}），双均线成功捕捉了主要波段。策略择时有效，适合当前市场环境。  
**建议**：保持当前参数，可考虑加入价值因子过滤（如PE≤20）进一步提高安全性。  
"""
            elif main_strategy == "RSI策略":
                if perf == "亏损":
                    advice = f"""
**📉 RSI策略亏损**  
策略年化收益率 {strategy_ret*100:.2f}%，基准年化收益率 {benchmark_ret*100:.2f}%。  
该股票波动率 {volatility:.2%}，趋势强度 {trend_strength:.3f}。RSI策略试图捕捉价格超卖/超买后的回归，在单边趋势市场中，RSI可能长时间处于超买或超卖区域，价格不回头，导致策略频繁逆势交易而亏损。  
**可尝试的调整**：增加趋势过滤（仅在震荡市中交易），或放宽超买超卖阈值，或改用双均线策略。  
"""
                elif perf == "正收益但未跑赢基准":
                    advice = f"""
**📈 RSI策略盈利但未跑赢基准**  
策略年化收益率 {strategy_ret*100:.2f}%，基准年化收益率 {benchmark_ret*100:.2f}%。  
该股票具有一定的均值回归特性，RSI策略在波动区间内获得部分收益，但整体涨幅落后于基准，可能因为部分趋势行情中过早卖出。  
**可尝试的调整**：调整RSI周期或阈值（例如周期14→21，阈值70/30→80/20），或结合趋势判断。  
"""
                else:
                    advice = f"""
**🚀 RSI策略跑赢基准**  
策略年化收益率 {strategy_ret*100:.2f}%，基准年化收益率 {benchmark_ret*100:.2f}%。  
该股票表现出明显的均值回归特征，RSI策略成功捕捉了波动区间的买卖点。策略高抛低吸有效，适合震荡市场。  
**建议**：可配合成交量确认增强信号可靠性。  
"""
            else:
                if perf == "亏损":
                    advice = f"""
**📉 布林带策略亏损**  
策略年化收益率 {strategy_ret*100:.2f}%，基准年化收益率 {benchmark_ret*100:.2f}%。  
该股票波动率 {volatility:.2f}，趋势强度 {trend_strength:.3f}。布林带策略试图在价格触及轨道时反向交易，在趋势突破行情中，价格可能持续沿一个方向运行，导致反复止损。  
**可尝试的调整**：放宽标准差倍数（如2.5），或改用趋势跟踪策略。  
"""
                elif perf == "正收益但未跑赢基准":
                    advice = f"""
**📈 布林带策略盈利但未跑赢基准**  
策略年化收益率 {strategy_ret*100:.2f}%，基准年化收益率 {benchmark_ret*100:.2f}%。  
该股票在一定区间内波动，布林带策略获得部分收益，但可能遇到趋势突破导致部分回吐。  
**可尝试的调整**：结合ATR动态调整止损，或在突破时暂停交易。  
"""
                else:
                    advice = f"""
**🚀 布林带策略跑赢基准**  
策略年化收益率 {strategy_ret*100:.2f}%，基准年化收益率 {benchmark_ret*100:.2f}%。  
该股票波动率适中，价格在布林带内规律运动，策略高抛低吸成功。适合区间震荡行情。  
**建议**：关注带宽收窄后的方向选择，避免在趋势启动时逆势交易。  
"""
            st.markdown(advice)

        st.subheader("策略回测绩效")
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("年化收益率（策略）", f"{metrics.get('年化收益率（策略）',0)*100:.2f}%")
        col_b.metric("夏普比率", f"{metrics.get('夏普比率',0):.2f}")
        col_c.metric("最大回撤", f"{metrics.get('最大回撤',0)*100:.2f}%")
        bench_ret = metrics.get('年化收益率（基准）', 0)
        st.caption(f"📈 基准（沪深300）年化收益率：{bench_ret*100:.2f}%")

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

        last_signal = df_strat[df_strat['signal'].notna() & (df_strat['signal'] != 0)].iloc[-1] if len(df_strat[df_strat['signal'].notna() & (df_strat['signal'] != 0)]) > 0 else None
        if last_signal is not None:
            explanation = explain_signal(last_signal, main_strategy, main_params)
            if explanation:
                st.info(explanation)

        fig_curve = plot_equity_curve(df_strat, benchmark_col='benchmark_net', strategy_col='strategy_net')
        st.pyplot(fig_curve)

        with st.expander("📊 历史信号表现统计", expanded=False):
            stats = signal_historical_performance(df_strat)
            if stats:
                for period, data in stats.items():
                    col1, col2 = st.columns(2)
                    col1.metric(f"{period} 平均收益", f"{data['平均收益']:.2%}")
                    col2.metric(f"{period} 胜率", f"{data['胜率']:.2%}")
            else:
                st.info("无买入信号记录")

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

        if config.get('enable_heatmap', False):
            st.subheader("🔥 双均线夏普热力图")
            with st.spinner("网格搜索中..."):
                short_vals, long_vals, sharpe_mat = grid_search_ma(df, config['hm_short'], config['hm_long'], step=config['hm_step'],
                                                                   commission=config['commission'], slippage=config['slippage'],
                                                                   initial_capital=config['initial_capital'], rebalance_freq=config['rebalance_freq'])
            fig_heat = go.Figure(data=go.Heatmap(x=long_vals, y=short_vals, z=sharpe_mat, colorscale='RdYlGn', zmid=0))
            st.plotly_chart(fig_heat, width='stretch')

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