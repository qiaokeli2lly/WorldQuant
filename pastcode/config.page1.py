import streamlit as st
import pandas as pd

def show():
    st.title("📊 MiniQuant 量化分析平台")
    st.markdown("### 1️⃣ 选择股票与策略参数")

    # 从 session_state 读取上次配置，用于填充默认值
    if 'config' in st.session_state:
        cfg = st.session_state.config
        default_symbol = cfg.get('symbol', '600519')
        default_start = cfg.get('start_date', pd.to_datetime("2022-01-01"))
        default_end = cfg.get('end_date', pd.to_datetime("2024-12-31"))
        default_ma_periods = cfg.get('ma_periods', [5,20,60])
        default_bb_period = cfg.get('bb_period', 20)
        default_bb_std = cfg.get('bb_std', 2.0)
        default_show_candlestick = cfg.get('show_candlestick', True)
        default_show_rsi = cfg.get('show_rsi', True)
        default_show_macd = cfg.get('show_macd', False)
        default_show_kdj = cfg.get('show_kdj', False)
        default_rsi_period = cfg.get('rsi_period', 14)
        default_rsi_overbought = cfg.get('rsi_overbought', 70)
        default_rsi_oversold = cfg.get('rsi_oversold', 30)
        default_strategy = cfg.get('strategy', "双均线")
        # 策略参数
        if default_strategy == "双均线":
            default_short_ma = cfg.get('params', {}).get('short_ma', 5)
            default_long_ma = cfg.get('params', {}).get('long_ma', 20)
        elif default_strategy == "RSI策略":
            default_rsi_period_strat = cfg.get('params', {}).get('period', 14)
            default_rsi_os_strat = cfg.get('params', {}).get('oversold', 30)
            default_rsi_ob_strat = cfg.get('params', {}).get('overbought', 70)
        else:
            default_bb_period_strat = cfg.get('params', {}).get('period', 20)
            default_bb_std_strat = cfg.get('params', {}).get('std_dev', 2.0)
        default_commission = cfg.get('commission', 0.001)
        default_slippage = cfg.get('slippage', 0.001)
        default_enable_compare = cfg.get('enable_compare', False)
        default_compare_strategies = cfg.get('compare_strategies', [])
        default_enable_heatmap = cfg.get('enable_heatmap', False)
        default_hm_short = cfg.get('hm_short', (3,15))
        default_hm_long = cfg.get('hm_long', (20,60))
        default_hm_step = cfg.get('hm_step', 2)
    else:
        default_symbol = '600519'
        default_start = pd.to_datetime("2022-01-01")
        default_end = pd.to_datetime("2024-12-31")
        default_ma_periods = [5,20,60]
        default_bb_period = 20
        default_bb_std = 2.0
        default_show_candlestick = True
        default_show_rsi = True
        default_show_macd = False
        default_show_kdj = False
        default_rsi_period = 14
        default_rsi_overbought = 70
        default_rsi_oversold = 30
        default_strategy = "双均线"
        default_short_ma = 5
        default_long_ma = 20
        default_rsi_period_strat = 14
        default_rsi_os_strat = 30
        default_rsi_ob_strat = 70
        default_bb_period_strat = 20
        default_bb_std_strat = 2.0
        default_commission = 0.001
        default_slippage = 0.001
        default_enable_compare = False
        default_compare_strategies = []
        default_enable_heatmap = False
        default_hm_short = (3,15)
        default_hm_long = (20,60)
        default_hm_step = 2

    with st.form("config_form"):
        col1, col2 = st.columns(2)
        with col1:
            symbol = st.text_input("📈 股票代码", value=default_symbol, help="6位数字A股代码").upper()
        with col2:
            start_date = st.date_input("📅 开始日期", value=default_start)
            end_date = st.date_input("📅 结束日期", value=default_end)

        st.subheader("📊 技术指标参数")
        ma_periods = st.multiselect("移动平均线周期", options=[5,10,20,30,60,120,250], default=default_ma_periods,
                                    help="选择要在K线图上显示的均线。")
        bb_period = st.slider("布林带周期", 10, 50, default_bb_period, help="计算布林带中轨的移动平均周期。")
        bb_std = st.slider("布林带标准差倍数", 1.0, 3.0, default_bb_std, step=0.1, help="上下轨与中轨的距离倍数。")
        show_candlestick = st.radio("主图样式", ["K线", "收盘线"], index=0 if default_show_candlestick else 1) == "K线"

        st.subheader("📉 副图指标")
        show_rsi = st.checkbox("RSI", value=default_show_rsi)
        show_macd = st.checkbox("MACD", value=default_show_macd)
        show_kdj = st.checkbox("KDJ", value=default_show_kdj)
        if show_rsi:
            rsi_period = st.slider("RSI周期", 5, 30, default_rsi_period)
            rsi_overbought = st.slider("RSI超买线", 60, 90, default_rsi_overbought)
            rsi_oversold = st.slider("RSI超卖线", 10, 40, default_rsi_oversold)

        st.subheader("⚙️ 策略回测参数")
        strategy = st.selectbox("选择策略", ["双均线", "RSI策略", "布林带策略"], index=["双均线", "RSI策略", "布林带策略"].index(default_strategy))
        
        if strategy == "双均线":
            st.markdown("""
            **📖 策略原理**：当短期均线上穿长期均线（金叉）时买入，下穿（死叉）时卖出。适用于趋势明显的行情。
            - **参考因子**：短期均线（默认5日）、长期均线（默认20日）
            - **参数调整**：缩短短期均线使信号更敏感，拉长长期均线减少噪音。
            """)
            short_ma = st.slider("短期均线", 2, 50, default_short_ma, help="短期均线周期，数值越小对价格变化越敏感。")
            long_ma = st.slider("长期均线", 10, 200, default_long_ma, help="长期均线周期，数值越大趋势越平缓。")
            params = {'short_ma': short_ma, 'long_ma': long_ma}
        elif strategy == "RSI策略":
            st.markdown("""
            **📖 策略原理**：RSI低于超卖线时买入（预期反弹），高于超买线时卖出（预期回调）。适用于震荡行情。
            - **参考因子**：RSI周期（默认14）、超卖线（30）、超买线（70）
            - **参数调整**：周期越短信号越敏感；强趋势中可放宽阈值。
            """)
            rsi_period_strat = st.slider("RSI周期", 5, 30, default_rsi_period_strat, help="计算RSI的周期，通常14。")
            rsi_oversold_strat = st.slider("买入阈值(RSI<)", 10, 40, default_rsi_os_strat, help="当RSI低于此值时买入。")
            rsi_overbought_strat = st.slider("卖出阈值(RSI>)", 60, 90, default_rsi_ob_strat, help="当RSI高于此值时卖出。")
            params = {'period': rsi_period_strat, 'oversold': rsi_oversold_strat, 'overbought': rsi_overbought_strat}
        else:
            st.markdown("""
            **📖 策略原理**：价格触及下轨时买入（超卖反弹），触及上轨时卖出（超买回落）。适合波动率交易。
            - **参考因子**：布林带周期（默认20）、标准差倍数（默认2）
            - **参数调整**：倍数越大通道越宽，触及概率越低。
            """)
            bb_period_strat = st.slider("布林带周期", 10, 50, default_bb_period_strat, help="计算布林带中轨的周期。")
            bb_std_strat = st.slider("标准差倍数", 1.0, 3.0, default_bb_std_strat, step=0.1, help="通道宽度倍数。")
            params = {'period': bb_period_strat, 'std_dev': bb_std_strat}
        
        commission = st.number_input("手续费率", value=default_commission, format="%.4f", help="单边手续费，例如0.001代表0.1%")
        slippage = st.number_input("滑点", value=default_slippage, format="%.4f", help="成交价差，通常0.05%~0.1%")

        with st.expander("📈 高级选项（多策略对比、热力图）"):
            enable_compare = st.checkbox("启用多策略对比", value=default_enable_compare)
            if enable_compare:
                compare_strategies = st.multiselect("选择对比策略", ["双均线", "RSI策略", "布林带策略"], default=default_compare_strategies)
            else:
                compare_strategies = []
            enable_heatmap = st.checkbox("启用双均线热力图", value=default_enable_heatmap)
            if enable_heatmap:
                hm_short = st.slider("短期均线范围", 2, 30, default_hm_short, help="短期均线扫描范围")
                hm_long = st.slider("长期均线范围", 10, 100, default_hm_long, help="长期均线扫描范围")
                hm_step = st.slider("步长", 1, 5, default_hm_step)
            else:
                hm_short = hm_long = hm_step = None

        submitted = st.form_submit_button("🚀 开始分析", use_container_width=True)
        
        if submitted:
            st.session_state.config = {
                'symbol': symbol, 'start_date': start_date, 'end_date': end_date,
                'ma_periods': ma_periods, 'bb_period': bb_period, 'bb_std': bb_std,
                'show_candlestick': show_candlestick,
                'show_rsi': show_rsi, 'show_macd': show_macd, 'show_kdj': show_kdj,
                'rsi_period': rsi_period, 'rsi_overbought': rsi_overbought, 'rsi_oversold': rsi_oversold,
                'strategy': strategy, 'params': params,
                'commission': commission, 'slippage': slippage,
                'enable_compare': enable_compare, 'compare_strategies': compare_strategies,
                'enable_heatmap': enable_heatmap, 'hm_short': hm_short, 'hm_long': hm_long, 'hm_step': hm_step
            }
            st.session_state.page = 'result'
            st.rerun()