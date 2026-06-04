import streamlit as st
import pandas as pd

def show():
    st.title("📊 MiniQuant 量化分析平台")
    st.markdown("### 1️⃣ 选择股票与策略参数")

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
        default_enable_trend_filter = cfg.get('enable_trend_filter', False)
        default_enable_volume_filter = cfg.get('enable_volume_filter', False)
        default_enable_dynamic_stop = cfg.get('enable_dynamic_stop', False)
        default_stop_loss_atr_mult = cfg.get('stop_loss_atr_mult', 2.0)
        default_enable_value_filter = cfg.get('enable_value_filter', False)
        default_value_logic = cfg.get('value_logic', 'AND')
        default_enable_pe = cfg.get('enable_pe', False)
        default_pe_max = cfg.get('pe_max', 20.0)
        default_enable_pb = cfg.get('enable_pb', False)
        default_pb_max = cfg.get('pb_max', 3.0)
        default_enable_mcap = cfg.get('enable_mcap', False)
        default_min_mcap = cfg.get('min_mcap', 100.0)
        default_enable_roe = cfg.get('enable_roe', False)
        default_min_roe = cfg.get('min_roe', 15.0)
        default_enable_gpm = cfg.get('enable_gpm', False)
        default_min_gpm = cfg.get('min_gpm', 20.0)
        default_enable_npm = cfg.get('enable_npm', False)
        default_min_npm = cfg.get('min_npm', 10.0)
        default_enable_debt = cfg.get('enable_debt', False)
        default_max_debt = cfg.get('max_debt', 60.0)
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
        default_enable_trend_filter = False
        default_enable_volume_filter = False
        default_enable_dynamic_stop = False
        default_stop_loss_atr_mult = 2.0
        default_enable_value_filter = False
        default_value_logic = 'AND'
        default_enable_pe = False
        default_pe_max = 20.0
        default_enable_pb = False
        default_pb_max = 3.0
        default_enable_mcap = False
        default_min_mcap = 100.0
        default_enable_roe = False
        default_min_roe = 15.0
        default_enable_gpm = False
        default_min_gpm = 20.0
        default_enable_npm = False
        default_min_npm = 10.0
        default_enable_debt = False
        default_max_debt = 60.0

    # 热门股票
    st.subheader("🔥 热门股票")
    popular = {
        "寒武纪": "688256", "澜起科技": "688008", "中际旭创": "300308", "海光信息": "688041",
        "宁德时代": "300750", "贵州茅台": "600519", "紫金矿业": "601899", "威龙股份": "603779",
        "达实智能": "002421", "京能电力": "600578", "天孚通信": "300502", "胜宏科技": "300476",
        "北方华创": "002371"
    }
    cols = st.columns(3)
    for i, (name, code) in enumerate(popular.items()):
        with cols[i % 3]:
            if st.button(name, key=f"pop_{code}"):
                st.session_state['symbol'] = code

    if 'symbol' not in st.session_state:
        st.session_state['symbol'] = default_symbol
    symbol = st.text_input("📈 股票代码", value=st.session_state['symbol']).upper()
    st.session_state['symbol'] = symbol

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("📅 开始日期", value=default_start)
    with col2:
        end_date = st.date_input("📅 结束日期", value=default_end)

    strategy = st.selectbox("选择主策略", ["双均线", "RSI策略", "布林带策略"],
                            index=["双均线", "RSI策略", "布林带策略"].index(default_strategy))

    if strategy == "双均线":
        short_ma = st.slider("短期均线", 2, 50, default_short_ma)
        long_ma = st.slider("长期均线", 10, 200, default_long_ma)
        params = {'short_ma': short_ma, 'long_ma': long_ma}
    elif strategy == "RSI策略":
        rsi_period_strat = st.slider("RSI周期", 5, 30, default_rsi_period_strat)
        rsi_os_strat = st.slider("买入阈值(RSI<)", 10, 40, default_rsi_os_strat)
        rsi_ob_strat = st.slider("卖出阈值(RSI>)", 60, 90, default_rsi_ob_strat)
        params = {'period': rsi_period_strat, 'oversold': rsi_os_strat, 'overbought': rsi_ob_strat}
    else:
        bb_period_strat = st.slider("布林带周期", 10, 50, default_bb_period_strat)
        bb_std_strat = st.slider("标准差倍数", 1.0, 3.0, default_bb_std_strat, step=0.1)
        params = {'period': bb_period_strat, 'std_dev': bb_std_strat}

    with st.form("config_form"):
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

        st.subheader("🛡️ 策略优化选项")
        enable_trend_filter = st.checkbox("启用大盘趋势过滤", value=default_enable_trend_filter)
        enable_volume_filter = st.checkbox("启用成交量确认", value=default_enable_volume_filter)
        enable_dynamic_stop = st.checkbox("启用动态止损 (基于ATR)", value=default_enable_dynamic_stop)
        stop_loss_atr_mult = st.slider("ATR止损倍数", 1.0, 5.0, default_stop_loss_atr_mult, step=0.5,
                                       disabled=not enable_dynamic_stop)

        st.subheader("📊 价值因子过滤器 (开仓检查)")
        st.info("💡 提示：价值因子数据（PE、PB、ROE等）将在分析后以图表和数值形式展示。您可以在下方设置过滤条件，系统会在开仓时检查是否满足条件。")
        enable_value_filter = st.checkbox("启用价值因子过滤", value=default_enable_value_filter)
        if enable_value_filter:
            value_logic = st.radio("条件逻辑", ["AND", "OR"], index=0 if default_value_logic=="AND" else 1)
            st.markdown("**每日因子**")
            col1, col2 = st.columns(2)
            with col1:
                enable_pe = st.checkbox("启用 PE", value=default_enable_pe)
                pe_max = st.number_input("PE ≤", value=default_pe_max, step=5.0, disabled=not enable_pe)
            with col2:
                enable_pb = st.checkbox("启用 PB", value=default_enable_pb)
                pb_max = st.number_input("PB ≤", value=default_pb_max, step=0.5, disabled=not enable_pb)
            enable_mcap = st.checkbox("启用 总市值", value=default_enable_mcap)
            min_mcap = st.number_input("总市值 ≥ (亿元)", value=default_min_mcap, step=50.0, disabled=not enable_mcap)
            st.markdown("**季度因子 (需填充)**")
            col1, col2 = st.columns(2)
            with col1:
                enable_roe = st.checkbox("启用 ROE", value=default_enable_roe)
                min_roe = st.number_input("ROE ≥ (%)", value=default_min_roe, step=5.0, disabled=not enable_roe)
                enable_gpm = st.checkbox("启用 毛利率", value=default_enable_gpm)
                min_gpm = st.number_input("毛利率 ≥ (%)", value=default_min_gpm, step=5.0, disabled=not enable_gpm)
            with col2:
                enable_npm = st.checkbox("启用 净利率", value=default_enable_npm)
                min_npm = st.number_input("净利率 ≥ (%)", value=default_min_npm, step=5.0, disabled=not enable_npm)
                enable_debt = st.checkbox("启用 资产负债率", value=default_enable_debt)
                max_debt = st.number_input("资产负债率 ≤ (%)", value=default_max_debt, step=10.0, disabled=not enable_debt)
        else:
            value_logic = 'AND'
            enable_pe = enable_pb = enable_mcap = enable_roe = enable_gpm = enable_npm = enable_debt = False
            pe_max = pb_max = min_mcap = min_roe = min_gpm = min_npm = max_debt = None

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

        submitted = st.form_submit_button("🚀 开始分析", width='stretch')

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
                'enable_trend_filter': enable_trend_filter,
                'enable_volume_filter': enable_volume_filter,
                'enable_dynamic_stop': enable_dynamic_stop,
                'stop_loss_atr_mult': stop_loss_atr_mult if enable_dynamic_stop else None,
                'enable_value_filter': enable_value_filter,
                'value_logic': value_logic,
                'enable_pe': enable_pe, 'pe_max': pe_max,
                'enable_pb': enable_pb, 'pb_max': pb_max,
                'enable_mcap': enable_mcap, 'min_mcap': min_mcap,
                'enable_roe': enable_roe, 'min_roe': min_roe,
                'enable_gpm': enable_gpm, 'min_gpm': min_gpm,
                'enable_npm': enable_npm, 'min_npm': min_npm,
                'enable_debt': enable_debt, 'max_debt': max_debt,
                'enable_compare': enable_compare, 'compare_strategies': compare_strategies,
                'compare_params': compare_params,
                'enable_heatmap': enable_heatmap,
                'hm_short': hm_short, 'hm_long': hm_long, 'hm_step': hm_step
            }
            st.session_state.page = 'result'
            st.rerun()