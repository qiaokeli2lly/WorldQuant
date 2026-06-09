# pages/config_page.py
import streamlit as st
import pandas as pd

def show():
    st.title("📊 MiniQuant 量化分析平台")
    st.markdown("### 1️⃣ 选择股票与策略参数")

    # ---------- 从 session_state 读取上次配置 ----------
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
        # 默认值
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

    # ---------- 热门股票 ----------
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

    # 日期选择
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("📅 开始日期", value=default_start)
        st.caption("回测起始日，建议包含至少1年数据。")
    with col2:
        end_date = st.date_input("📅 结束日期", value=default_end)
        st.caption("回测结束日，通常设为最近一个交易日。")

    # ---------- 参数说明与技巧折叠面板 ----------
    with st.expander("📖 参数说明与技巧（点击展开）", expanded=False):
        st.markdown("""
        ### 🎯 策略选择

        - **双均线**：追涨杀跌，适合有明显上涨或下跌趋势的股票。  
          *比喻*：就像开车跟着前车走，前车加速你就加速，减速你就减速。  
          *副作用*：在横盘震荡时会频繁金叉死叉，反复亏损。  
          *何时用*：你判断未来会出现单边大行情。

        - **RSI策略**：高抛低吸，适合横盘震荡的股票。  
          *比喻*：像温度计，太高了（>70）可能降温，太低了（<30）可能回暖。  
          *副作用*：在单边牛市中，RSI可能长期高于70，过早卖出会踏空。  
          *何时用*：你判断股价会在一个区间内来回波动。

        - **布林带策略**：轨道内高抛低吸，适合有明确波动区间的股票。  
          *比喻*：股价就像弹力球，碰到上轨弹回，碰到下轨弹起。  
          *副作用*：当股价突破轨道形成趋势时，会反复止损。  
          *何时用*：股价波动稳定，未出现大趋势。

        ### ⚙️ 策略参数调整

        - **均线周期**：周期越小，信号越频繁（短线），但假信号也多；周期越大，信号越平滑（长线），但反应迟钝。  
        - **RSI周期/阈值**：周期短敏感，周期长平滑。阈值在牛市中可放宽（如超买线80，超卖线20），避免过早逆势交易。  
        - **布林带倍数**：倍数越大，通道越宽，触及轨道的概率越低；倍数越小，信号越多。

        ### 🛡️ 过滤条件

        - **价值因子过滤**：只在PE、PB等满足条件时开仓，避免在高估值时买入。  
          *好处*：防止追高，减少亏损。  
          *坏处*：牛市中可能因为估值一直偏高而空仓，踏空行情。  
          *建议*：估值高位或熊市中开启；牛市中可关闭。

        - **大盘趋势过滤**：只在沪深300指数20日均线上方时交易。  
          *好处*：牛市赚钱，熊市空仓保本。  
          *坏处*：可能错过个股独立行情（大盘跌但个股涨）。  
          *建议*：系统风险大时开启，否则关闭。

        - **成交量确认**：放量才交易，过滤假突破。  
          *副作用*：会错过缩量上涨的牛股。

        ### 📉 风险控制

        - **动态止损（ATR）**：根据波动率自动调整止损距离。  
          *比喻*：波动大时放宽止损，避免被正常波动扫出；波动小时收紧止损，保护利润。  
          *建议*：倍数设2~3，太小时容易频繁止损。

        - **调仓频率**：越高交易成本越大，但能更快适应市场；越低越省手续费，但反应慢。  
          *建议*：短线选高频率，长线选低频率。

        - **手续费/滑点**：实盘必须设置，否则回测结果偏乐观。一般设为0.05%~0.2%。

        ### 💰 价值因子（基本面）

        - **PE（市盈率）**：股价 ÷ 每股收益，越低越便宜。价值股<15，成长股<30。  
        - **PB（市净率）**：股价 ÷ 每股净资产，越低越便宜。银行股<1，消费股<5。  
        - **ROE（净资产收益率）**：净利润 ÷ 净资产，越高越会赚钱。通常要求>15%。  
        - **资产负债率**：总负债 ÷ 总资产，>60%风险较高。

        ### 🧠 多因子权重

        - 各因子权重之和应等于1。  
        - 如果您看好**趋势**，增加 `momentum` 和 `new_momentum` 权重；  
        - 如果看好**低波动**，增加 `volatility`；  
        - 如果看好**价量配合**，增加 `rpv`。  
        - 可先使用默认权重，再根据回测结果微调。

        ### 📊 热力图

        - 展示不同均线参数组合下的夏普比率，颜色越绿表示表现越好。  
        - 可以帮助您快速找到最优参数，但注意过拟合风险（不要只盯着历史最优）。
        """)

    # 策略选择（增加场景化描述）
    strategy = st.selectbox(
        "选择主策略",
        ["双均线", "RSI策略", "布林带策略"],
        index=["双均线", "RSI策略", "布林带策略"].index(default_strategy),
        help="根据股票走势选择：**趋势明显选双均线，震荡行情选RSI，波动规律选布林带**。"
    )
    # 策略适用场景提示
    if strategy == "双均线":
        st.info("📈 **双均线**：适合有**明显涨跌趋势**的股票。金叉买，死叉卖。\n"
                "⚠️ 震荡市会频繁假信号，来回亏损。")
    elif strategy == "RSI策略":
        st.info("📊 **RSI策略**：适合**横盘震荡**的股票。超卖买，超买卖。\n"
                "⚠️ 单边牛市会过早卖出，踏空行情。")
    else:
        st.info("📐 **布林带**：适合**波动规律**的股票。下轨买，上轨卖。\n"
                "⚠️ 股价突破轨道时可能反复止损。")

    # 主策略参数控件
    if strategy == "双均线":
        st.markdown("**📖 策略原理**：短期均线上穿长期均线（金叉）买入，下穿（死叉）卖出。")
        short_ma = st.slider("短期均线", 2, 50, default_short_ma)
        st.caption("数值越小，信号越敏感（短线）；越大越平滑（长线）。")
        long_ma = st.slider("长期均线", 10, 200, default_long_ma)
        st.caption("通常设为短期均线的3-4倍。金叉买入，死叉卖出。")
        params = {'short_ma': short_ma, 'long_ma': long_ma}
    elif strategy == "RSI策略":
        st.markdown("**📖 策略原理**：RSI低于超卖线买入（预期反弹），高于超买线卖出（预期回调）。")
        rsi_period_strat = st.slider("RSI周期", 5, 30, default_rsi_period_strat)
        st.caption("周期越短，信号越频繁（适合短线）；越长越平滑。")
        rsi_os_strat = st.slider("买入阈值(RSI<)", 10, 40, default_rsi_os_strat)
        st.caption("RSI低于此值视为超卖，可能反弹。牛市可调低（如20）。")
        rsi_ob_strat = st.slider("卖出阈值(RSI>)", 60, 90, default_rsi_ob_strat)
        st.caption("RSI高于此值视为超买，可能回调。牛市可调高（如80）。")
        params = {'period': rsi_period_strat, 'oversold': rsi_os_strat, 'overbought': rsi_ob_strat}
    else:
        st.markdown("**📖 策略原理**：价格触及下轨买入（超卖反弹），触及上轨卖出（超买回落）。")
        bb_period_strat = st.slider("布林带周期", 10, 50, default_bb_period_strat)
        st.caption("计算中轨的移动平均周期，常用20。")
        bb_std_strat = st.slider("标准差倍数", 1.0, 3.0, default_bb_std_strat, step=0.1)
        st.caption("倍数越大，通道越宽，触及轨道的概率越低。")
        params = {'period': bb_period_strat, 'std_dev': bb_std_strat}

    # 其他参数放在表单内
    with st.form("config_form"):
        st.subheader("📊 技术指标参数")
        ma_periods = st.multiselect("移动平均线周期", [5,10,20,30,60,120,250], default=default_ma_periods)
        st.caption("选择要在K线图上显示的均线。短期均线（5、10）反应快，长期均线（60、120）看大趋势。")
        bb_period = st.slider("布林带周期", 10, 50, default_bb_period)
        st.caption("计算布林带中轨的移动平均周期，常用20。")
        bb_std = st.slider("布林带标准差倍数", 1.0, 3.0, default_bb_std, step=0.1)
        st.caption("上下轨与中轨的距离倍数。倍数越大通道越宽。")
        show_candlestick = st.radio("主图样式", ["K线", "收盘线"], index=0 if default_show_candlestick else 1) == "K线"
        st.caption("K线包含开、高、低、收；收盘线只显示收盘价连线，更简洁。")

        st.subheader("📉 副图指标")
        show_rsi = st.checkbox("RSI", value=default_show_rsi)
        st.caption("相对强弱指数，判断超买超卖。")
        show_macd = st.checkbox("MACD", value=default_show_macd)
        st.caption("指数平滑异同移动平均线，判断趋势和动能。")
        show_kdj = st.checkbox("KDJ", value=default_show_kdj)
        st.caption("随机指标，短线买卖参考。")
        if show_rsi:
            rsi_period = st.slider("RSI周期", 5, 30, default_rsi_period)
            st.caption("计算RSI的天数。周期越短越敏感，越长越平滑。")
            rsi_overbought = st.slider("RSI超买线", 60, 90, default_rsi_overbought)
            st.caption("RSI高于此值视为超买，可能回调。")
            rsi_oversold = st.slider("RSI超卖线", 10, 40, default_rsi_oversold)
            st.caption("RSI低于此值视为超卖，可能反弹。")

        st.subheader("⚙️ 回测参数")
        initial_capital = st.number_input("初始资金(元)", value=default_initial_capital, step=10000)
        st.caption("回测起始资金，默认10万元。")
        rebalance_freq = st.selectbox("调仓频率", ["每日", "每周", "每月"], index=["每日","每周","每月"].index({ 'D':'每日', 'W':'每周', 'M':'每月' }[default_rebalance_freq]))
        # 调仓频率成本提示
        if rebalance_freq == "每日":
            st.warning("⚠️ 每日调仓交易次数多（年约250次），**手续费和滑点会大幅侵蚀利润**。实盘建议至少设0.1%手续费。")
        elif rebalance_freq == "每周":
            st.info("💡 每周调仓年约50次，平衡了反应速度和交易成本。")
        freq_map = {"每日": "D", "每周": "W", "每月": "M"}
        rebalance_freq_code = freq_map[rebalance_freq]
        commission = st.number_input("手续费率", value=default_commission, format="%.4f",
                                     help="单边交易成本。实盘通常0.001~0.003（万分之一到万分之三）。")
        if commission < 0.001 and rebalance_freq == "每日":
            st.warning("⚠️ 你设的手续费率偏低，实盘成本可能更高，回测结果会偏乐观。建议至少设0.001。")
        st.caption("单边交易成本，例如0.001代表0.1%。实盘务必设置。")
        slippage = st.number_input("滑点", value=default_slippage, format="%.4f",
                                   help="因流动性导致的成交价差，实盘通常0.0005~0.002。")
        st.caption("因流动性导致的成交价差，通常设为0.05%~0.2%。")

        st.subheader("🛡️ 策略优化选项")
        enable_trend_filter = st.checkbox("启用大盘趋势过滤", value=default_enable_trend_filter)
        st.caption("只在沪深300指数20日均线之上时交易。牛市赚钱，熊市空仓。")
        if enable_trend_filter:
            st.info("💡 开启后，**熊市期间策略会空仓**，净值走平。若回测期包含熊市，交易次数会很少。")
        enable_volume_filter = st.checkbox("启用成交量确认", value=default_enable_volume_filter)
        st.caption("信号出现时，成交量需大于过去20日均量的1.5倍，可过滤假信号。")
        enable_dynamic_stop = st.checkbox("启用动态止损 (基于ATR)", value=default_enable_dynamic_stop)
        st.caption("根据波动率自动调整止损距离，比固定百分比更科学。")
        if enable_dynamic_stop:
            st.info("💡 ATR是14天平均真实波幅，**倍数越大越能容忍波动**（不易被震出），但止损距离更远。")
        stop_loss_atr_mult = st.slider("ATR止损倍数", 1.0, 5.0, default_stop_loss_atr_mult, step=0.5,
                                       disabled=not enable_dynamic_stop)
        st.caption("倍数越小越容易止损，倍数越大越能容忍波动。建议2~3。")

        # 价值因子过滤器（增加当前估值提示）
        st.subheader("📊 价值因子过滤器 (开仓检查)")
        st.info("💡 提示：价值因子数据（PE、PB、ROE等）将在分析后以图表和数值形式展示。您可以在下方设置过滤条件，系统会在开仓时检查是否满足条件。")
        enable_value_filter = st.checkbox("启用价值因子过滤", value=default_enable_value_filter)
        st.caption("只在估值合理（如PE<20）且盈利质量高时买入，避免追高。但牛市中可能踏空。")
        if enable_value_filter:
            # 尝试获取当前估值数据（如果已经在session中）
            current_pe = None
            current_pb = None
            if 'latest_fundamental' in st.session_state:
                fund = st.session_state.latest_fundamental
                current_pe = fund.get('PE')
                current_pb = fund.get('PB')
            if current_pe is not None or current_pb is not None:
                st.info(f"📊 当前估值参考：PE={current_pe} | PB={current_pb}（基于最新数据）")
            else:
                st.caption("💡 运行分析后将显示当前股票的PE/PB，帮助您设定合理的阈值。")
            
            value_logic = st.radio("条件逻辑", ["AND", "OR"], index=0 if default_value_logic=="AND" else 1)
            st.caption("AND：所有启用因子必须同时满足；OR：任一满足即可。")
            st.markdown("**每日因子**")
            col1, col2 = st.columns(2)
            with col1:
                enable_pe = st.checkbox("启用 PE", value=default_enable_pe)
                st.caption("市盈率，越低越便宜。")
                pe_max = st.number_input("PE ≤", value=default_pe_max, step=5.0, disabled=not enable_pe)
                if enable_pe and current_pe is not None:
                    if pe_max < current_pe:
                        st.warning(f"⚠️ 当前PE={current_pe}，你设的PE≤{pe_max}比现价严格，**可能导致策略长期空仓**。")
                st.caption("建议：价值股15-20，成长股25-30。设置过低可能错过机会。")
            with col2:
                enable_pb = st.checkbox("启用 PB", value=default_enable_pb)
                st.caption("市净率，越低表示资产估值越便宜。")
                pb_max = st.number_input("PB ≤", value=default_pb_max, step=0.5, disabled=not enable_pb)
                if enable_pb and current_pb is not None:
                    if pb_max < current_pb:
                        st.warning(f"⚠️ 当前PB={current_pb}，你设的PB≤{pb_max}比现价严格，**可能导致策略长期空仓**。")
                st.caption("常见阈值：银行股<1，消费股<5。")
            enable_mcap = st.checkbox("启用 总市值", value=default_enable_mcap)
            st.caption("总市值（亿元），用于过滤小盘股（防流动性风险）或大盘股。")
            min_mcap = st.number_input("总市值 ≥ (亿元)", value=default_min_mcap, step=50.0, disabled=not enable_mcap)
            st.caption("只交易市值大于此值的股票，避免小盘股高波动。")

            st.markdown("**季度因子 (需填充)**")
            col1, col2 = st.columns(2)
            with col1:
                enable_roe = st.checkbox("启用 ROE", value=default_enable_roe)
                st.caption("净资产收益率，衡量盈利能力。越高越好。")
                min_roe = st.number_input("ROE ≥ (%)", value=default_min_roe, step=5.0, disabled=not enable_roe)
                st.caption("通常要求ROE > 15%才算优质。")
                enable_gpm = st.checkbox("启用 毛利率", value=default_enable_gpm)
                st.caption("毛利率高表示产品竞争力强。")
                min_gpm = st.number_input("毛利率 ≥ (%)", value=default_min_gpm, step=5.0, disabled=not enable_gpm)
                st.caption("高于20%较好，科技/消费股可要求更高。")
            with col2:
                enable_npm = st.checkbox("启用 净利率", value=default_enable_npm)
                st.caption("净利率高说明盈利能力强。")
                min_npm = st.number_input("净利率 ≥ (%)", value=default_min_npm, step=5.0, disabled=not enable_npm)
                st.caption("高于10%较健康。")
                enable_debt = st.checkbox("启用 资产负债率", value=default_enable_debt)
                st.caption("负债率过高风险大。")
                max_debt = st.number_input("资产负债率 ≤ (%)", value=default_max_debt, step=10.0, disabled=not enable_debt)
                st.caption("通常要求低于60%财务安全。")
        else:
            value_logic = 'AND'
            enable_pe = enable_pb = enable_mcap = enable_roe = enable_gpm = enable_npm = enable_debt = False
            pe_max = pb_max = min_mcap = min_roe = min_gpm = min_npm = max_debt = None

        # 高级选项（多策略对比、热力图）
        with st.expander("📈 高级选项（多策略对比、热力图）"):
            enable_compare = st.checkbox("启用多策略对比", value=default_enable_compare)
            st.caption("同时运行多个策略，对比资金曲线和绩效。")
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
            st.caption("网格搜索不同均线参数组合的夏普比率，可视化最优参数。")
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