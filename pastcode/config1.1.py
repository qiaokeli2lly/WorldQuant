import streamlit as st
import pandas as pd

def show():
    st.title("📊 MiniQuant 量化分析平台")
    st.markdown("### 1️⃣ 选择股票与策略参数")

    # 从 session_state 读取上次配置
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
        default_short_ma = cfg.get('params', {}).get('short_ma', 5)
        default_long_ma = cfg.get('params', {}).get('long_ma', 20)
        default_rsi_period_strat = cfg.get('params', {}).get('period', 14)
        default_rsi_os_strat = cfg.get('params', {}).get('oversold', 30)
        default_rsi_ob_strat = cfg.get('params', {}).get('overbought', 70)
        default_bb_period_strat = cfg.get('params', {}).get('period', 20)
        default_bb_std_strat = cfg.get('params', {}).get('std_dev', 2.0)
        default_commission = cfg.get('commission', 0.001)
        default_slippage = cfg.get('slippage', 0.001)
        default_initial_capital = cfg.get('initial_capital', 100000)
        default_rebalance_freq = cfg.get('rebalance_freq', 'D')
        default_enable_compare = cfg.get('enable_compare', False)
        default_compare_strategies = cfg.get('compare_strategies', [])
        default_compare_params = cfg.get('compare_params', {})
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
        default_initial_capital = 100000
        default_rebalance_freq = 'D'
        default_enable_compare = False
        default_compare_strategies = []
        default_compare_params = {}
        default_enable_heatmap = False
        default_hm_short = (3,15)
        default_hm_long = (20,60)
        default_hm_step = 2

    # 策略选择（放在表单外实时更新）
    strategy = st.selectbox("选择主策略", ["双均线", "RSI策略", "布林带策略"],
                            index=["双均线", "RSI策略", "布林带策略"].index(default_strategy))

    # 主策略参数控件
    if strategy == "双均线":
        st.markdown("**📖 策略原理**：短期均线上穿长期均线（金叉）买入，下穿（死叉）卖出。")
        short_ma = st.slider("短期均线", 2, 50, default_short_ma)
        long_ma = st.slider("长期均线", 10, 200, default_long_ma)
        params = {'short_ma': short_ma, 'long_ma': long_ma}
    elif strategy == "RSI策略":
        st.markdown("**📖 策略原理**：RSI低于超卖线买入，高于超买线卖出。")
        rsi_period_strat = st.slider("RSI周期", 5, 30, default_rsi_period_strat)
        rsi_os_strat = st.slider("买入阈值(RSI<)", 10, 40, default_rsi_os_strat)
        rsi_ob_strat = st.slider("卖出阈值(RSI>)", 60, 90, default_rsi_ob_strat)
        params = {'period': rsi_period_strat, 'oversold': rsi_os_strat, 'overbought': rsi_ob_strat}
    else:
        st.markdown("**📖 策略原理**：价格触及下轨买入，触及上轨卖出。")
        bb_period_strat = st.slider("布林带周期", 10, 50, default_bb_period_strat)
        bb_std_strat = st.slider("标准差倍数", 1.0, 3.0, default_bb_std_strat, step=0.1)
        params = {'period': bb_period_strat, 'std_dev': bb_std_strat}

    # 其他参数放在表单内
    with st.form("config_form"):
        col1, col2 = st.columns(2)
        with col1:
            symbol = st.text_input("📈 股票代码", value=default_symbol).upper()
        with col2:
            start_date = st.date_input("📅 开始日期", value=default_start)
            end_date = st.date_input("📅 结束日期", value=default_end)

        st.subheader("📊 技术指标参数")
        ma_periods = st.multiselect("移动平均线周期", [5,10,20,30,60,120,250], default=default_ma_periods)
        bb_period = st.slider("布林带周期", 10, 50, default_bb_period)
        bb_std = st.slider("布林带标准差倍数", 1.0, 3.0, default_bb_std, step=0.1)
        show_candlestick = st.radio("主图样式", ["K线", "收盘线"], index=0 if default_show_candlestick else 1) == "K线"

        st.subheader("📉 副图指标")
        show_rsi = st.checkbox("RSI", value=default_show_rsi)
        show_macd = st.checkbox("MACD", value=default_show_macd)
        show_kdj = st.checkbox("KDJ", value=default_show_kdj)
        if show_rsi:
            rsi_period = st.slider("RSI周期", 5, 30, default_rsi_period)
            rsi_overbought = st.slider("RSI超买线", 60, 90, default_rsi_overbought)
            rsi_oversold = st.slider("RSI超卖线", 10, 40, default_rsi_oversold)

        st.subheader("⚙️ 回测参数")
        initial_capital = st.number_input("初始资金(元)", value=default_initial_capital, step=10000)
        rebalance_freq = st.selectbox("调仓频率", ["每日", "每周", "每月"], index=["每日","每周","每月"].index({ 'D':'每日', 'W':'每周', 'M':'每月' }[default_rebalance_freq]))
        freq_map = {"每日": "D", "每周": "W", "每月": "M"}
        rebalance_freq_code = freq_map[rebalance_freq]
        commission = st.number_input("手续费率", value=default_commission, format="%.4f")
        slippage = st.number_input("滑点", value=default_slippage, format="%.4f")

        with st.expander("📈 高级选项（多策略对比、热力图）"):
            enable_compare = st.checkbox("启用多策略对比", value=default_enable_compare)
            compare_params = {}
            if enable_compare:
                compare_strategies = st.multiselect("选择对比策略", ["双均线", "RSI策略", "布林带策略"], default=default_compare_strategies)
                for cs in compare_strategies:
                    st.markdown(f"**{cs} 参数设置**")
                    if cs == "双均线":
                        cs_short = st.slider(f"{cs} - 短期均线", 2, 50, default_compare_params.get(f"{cs}_short_ma", 5), key=f"cs_{cs}_short")
                        cs_long = st.slider(f"{cs} - 长期均线", 10, 200, default_compare_params.get(f"{cs}_long_ma", 20), key=f"cs_{cs}_long")
                        compare_params[cs] = {'short_ma': cs_short, 'long_ma': cs_long}
                    elif cs == "RSI策略":
                        cs_period = st.slider(f"{cs} - RSI周期", 5, 30, default_compare_params.get(f"{cs}_period", 14), key=f"cs_{cs}_period")
                        cs_os = st.slider(f"{cs} - 买入阈值", 10, 40, default_compare_params.get(f"{cs}_oversold", 30), key=f"cs_{cs}_os")
                        cs_ob = st.slider(f"{cs} - 卖出阈值", 60, 90, default_compare_params.get(f"{cs}_overbought", 70), key=f"cs_{cs}_ob")
                        compare_params[cs] = {'period': cs_period, 'oversold': cs_os, 'overbought': cs_ob}
                    else:
                        cs_period = st.slider(f"{cs} - 布林带周期", 10, 50, default_compare_params.get(f"{cs}_period", 20), key=f"cs_{cs}_period")
                        cs_std = st.slider(f"{cs} - 标准差倍数", 1.0, 3.0, default_compare_params.get(f"{cs}_std", 2.0), step=0.1, key=f"cs_{cs}_std")
                        compare_params[cs] = {'period': cs_period, 'std_dev': cs_std}
            else:
                compare_strategies = []
            enable_heatmap = st.checkbox("启用双均线热力图", value=default_enable_heatmap)
            if enable_heatmap:
                hm_short = st.slider("短期均线范围", 2, 30, default_hm_short)
                hm_long = st.slider("长期均线范围", 10, 100, default_hm_long)
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
                'initial_capital': initial_capital, 'rebalance_freq': rebalance_freq_code,
                'enable_compare': enable_compare, 'compare_strategies': compare_strategies,
                'compare_params': compare_params,
                'enable_heatmap': enable_heatmap,
                'hm_short': hm_short, 'hm_long': hm_long, 'hm_step': hm_step
            }
            st.session_state.page = 'result'
            st.rerun() 