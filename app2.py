# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import tushare as ts

# ---- 新导入 ----
from pages.config_page import show as config_show
from pages.result_page import show as result_show
from backtest.portfolio_backtest import portfolio_backtest
from utils.stock_pool import get_predefined_pool
from config import FACTOR_NAME_CN                # 因子中英文映射
from intelligence.analyzer import analyze_stock

st.set_page_config(layout="wide", page_title="MiniQuant 量化分析平台", page_icon="📈")

# 初始化 session_state
if 'page' not in st.session_state:
    st.session_state.page = 'config'

# 获取全量A股列表（用于校验）
@st.cache_data
def get_all_a_stocks():
    import os
    import pandas as pd
    import tushare as ts
    cache_file = "a_stock_list.csv"
    if os.path.exists(cache_file):
        df = pd.read_csv(cache_file)
        return set(df['symbol'].astype(str).str.zfill(6))
    else:
        pro = ts.pro_api()
        df = pro.stock_basic(exchange='', list_status='L', fields='symbol')
        df['symbol'] = df['symbol'].astype(str).str.zfill(6)
        df.to_csv(cache_file, index=False)
        return set(df['symbol'])

# 创建选项卡
tab1, tab2, tab3 = st.tabs(["📈 单股票分析", "📊 多因子组合回测", "🧠 智能分析"])

# ================== 单股票分析 ==================
with tab1:
    if st.session_state.page == 'config':
        config_show()
    else:
        result_show()

# ================== 多因子组合回测 ==================
with tab2:
    st.header("多因子选股组合回测")
    
    # 价值说明框（包含回测逻辑解释）
    with st.expander("📚 这个页面能帮你做什么？", expanded=True):
        st.markdown("""
        **🎯 目标**：用多个量化因子（价值、动量、波动率等）对一篮子股票打分，每月选出得分最高的N只持有，看看能否跑赢沪深300指数。

        **💡 你能学到什么？**
        - 不同因子（比如PE、PB、RPV）对选股结果的影响
        - 调整因子权重后，组合收益、回撤、夏普比率的变化
        - 选股数量越多，组合越分散，但可能降低收益；选股越集中，波动越大
        - 调仓频率越高，交易成本越高，但能更快适应市场

        **📊 如何解读结果？**
        - **年化收益率**：策略平均每年赚多少（对比基准高低）
        - **最大回撤**：组合历史上最大亏损幅度，越小越稳健
        - **夏普比率**：每承担一单位风险能获得多少超额回报，大于1较好
        - **超额收益**：策略收益率减去基准收益率，正数说明跑赢大盘
        - **持仓列表**：观察每月选中的股票，判断风格（是否集中、行业分布）

        **🧠 回测基本逻辑**
        1. 在每个调仓日（每月末或每季度末），系统会为当前股票池中的所有股票计算各因子值。
        2. 将因子值去极值、标准化后，按用户设定的权重加权，得到每只股票的综合得分。
        3. 选出得分最高的 N 只股票，等权重买入（假设初始资金10万元）。
        4. 持有到下个调仓日，期间每日按持仓等权重计算组合收益率。
        5. 调仓时，卖出不在新组合中的股票，买入新入选的股票，并扣除手续费和滑点。
        6. 重复以上步骤，最终得到策略净值曲线，并与沪深300指数对比。
        """)

    # ---------- 1. 股票池选择 ----------
    if 'confirmed_stocks' not in st.session_state:
        st.session_state.confirmed_stocks = []
    if 'manual_stocks' not in st.session_state:
        st.session_state.manual_stocks = []

    col_pool, _ = st.columns([3, 1])
    with col_pool:
        stock_pool_option = st.selectbox("股票池", ["demo (50只龙头)", "沪深300 (需动态获取)"], index=0,
                                         help="demo池为50只行业龙头，沪深300需动态获取（耗时较长）")
        if stock_pool_option == "demo (50只龙头)":
            all_stocks = get_predefined_pool("demo")
        else:
            with st.spinner("正在获取沪深300成分股..."):
                all_stocks = get_predefined_pool("hs300")
        
        selected_from_pool = st.multiselect(
            "从股票池中选择（可多选）",
            options=all_stocks,
            default=[s for s in all_stocks if s in st.session_state.confirmed_stocks],
            help="勾选要参与回测的股票"
        )
        st.caption("💡 提示：至少选择2只股票才能进行组合对比。")

    # 手动添加股票
    st.markdown("### 或手动添加股票")
    manual_input = st.text_area("输入股票代码（用逗号、空格或换行分隔）", 
                                 help="例如：600519,000858,601318")
    st.caption("输入6位数字代码，系统会自动校验是否为A股。")
    col_add, col_clear = st.columns([1, 1])
    with col_add:
        if st.button("➕ 添加并校验"):
            import re
            codes = re.split(r'[,\s\n]+', manual_input.strip())
            codes = [c.strip() for c in codes if c.strip()]
            valid = []
            invalid = []
            all_a_stocks = get_all_a_stocks()
            for code in codes:
                if re.match(r'^\d{6}$', code) and code in all_a_stocks:
                    valid.append(code)
                else:
                    invalid.append(code)
            if invalid:
                st.warning(f"以下代码无效或非A股：{', '.join(invalid)}")
            if valid:
                new_stocks = list(set(st.session_state.confirmed_stocks + valid))
                st.session_state.confirmed_stocks = new_stocks
                st.session_state.manual_stocks = valid
                st.success(f"已添加 {len(valid)} 只股票")
                st.rerun()
    with col_clear:
        if st.button("🗑️ 清空手动添加"):
            st.session_state.confirmed_stocks = [s for s in st.session_state.confirmed_stocks if s in selected_from_pool]
            st.session_state.manual_stocks = []
            st.rerun()
    
    # 确认股票列表（同时重置权重为默认值）
    if st.button("✅ 确认股票列表", use_container_width=True):
        final_list = list(set(selected_from_pool + st.session_state.manual_stocks))
        if len(final_list) < 2:
            st.warning("至少需要选择2只股票才能进行组合回测。")
        else:
            st.session_state.confirmed_stocks = final_list
            # ---- 重置权重 ----
            weight_keys = [
                "weight_mom", "weight_rev", "weight_vol", "weight_rpv",
                "weight_newmom", "weight_combo", "weight_pe", "weight_pb"
            ]
            for key in weight_keys:
                if key in st.session_state:
                    del st.session_state[key]
            if "use_fundamental" in st.session_state:
                del st.session_state["use_fundamental"]
            st.session_state.expand_weights = True  # 自动展开权重面板
            st.success(f"已确认 {len(final_list)} 只股票，权重已重置为默认值。")
            st.rerun()
    
    # 显示当前股票列表
    final_stock_list = st.session_state.confirmed_stocks
    if final_stock_list:
        with st.expander(f"📋 当前股票列表（共{len(final_stock_list)}只）", expanded=True):
            st.write(final_stock_list)
            if len(final_stock_list) < 2:
                st.warning("⚠️ 当前股票数量少于2只，无法进行组合回测。请至少选择2只。")
    else:
        st.info("尚未选择股票，请从上方选择或手动添加。")

    # ---------- 2. 回测参数与权重设置 ----------
    st.markdown("---")
    st.subheader("⚙️ 回测参数与因子权重")

    # 重置默认权重按钮（放在表单外）
    col_reset, _ = st.columns([1, 3])
    with col_reset:
        if st.button("🔄 重置为默认权重"):
            weight_keys = [
                "weight_mom", "weight_rev", "weight_vol", "weight_rpv",
                "weight_newmom", "weight_combo", "weight_pe", "weight_pb"
            ]
            for key in weight_keys:
                if key in st.session_state:
                    del st.session_state[key]
            if "use_fundamental" in st.session_state:
                del st.session_state["use_fundamental"]
            st.toast("✅ 权重已重置为默认值，请展开面板查看")
            st.session_state.expand_weights = True
            st.rerun()

    if 'expand_weights' not in st.session_state:
        st.session_state.expand_weights = False

    with st.form("portfolio_form"):
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("回测开始日期", value=pd.to_datetime("2022-01-01"))
            st.caption("建议包含至少1年数据。")
        with col2:
            end_date = st.date_input("回测结束日期", value=pd.to_datetime("2024-12-31"))
            st.caption("因子表格将基于结束日期附近的有效交易日生成。")
        rebalance_freq = st.selectbox("调仓频率", ["每月", "每季度"], index=0)
        st.caption("频率越高交易成本越大，但能更快适应市场。")
        freq_map = {"每月": "M", "每季度": "Q"}
        rebalance_freq_code = freq_map[rebalance_freq]

        # ----- 选股数量滑块（优化）-----
        max_n = len(final_stock_list)
        if max_n < 2:
            st.warning("请先确认至少2只股票")
            top_n = 1
        else:
            # 默认值设为 min(5, max_n-1, max_n) 确保产生筛选
            default_top_n = min(5, max_n-1) if max_n > 2 else 1
            top_n = st.slider(
                "📌 每期持有几只股票？",
                min_value=1,
                max_value=max_n,
                value=max(1, default_top_n),
                step=1,
                help="选出的股票数量。**选股数小于池子大小时，权重调整才会影响结果**。"
            )
            # 智能提示
            if top_n == max_n:
                st.error(
                    f"⚠️ **注意**：你选了 {max_n} 只股票，持股数也是 {max_n} 只，意味着**全部买入**。\n"
                    "这时候调因子权重没有用，因为不管怎么打分，最后买的都是全部股票。\n"
                    f"**想看到权重的影响？把持股数调到 {max_n-1} 或更少。**"
                )
            elif top_n >= max_n * 0.8:
                st.warning(
                    f"💡 持股数 ({top_n}) 接近池子大小 ({max_n})，权重变化对持仓影响较小。\n"
                    "建议减少持股数（如选前 5~10 只），才能明显看到不同因子的筛选效果。"
                )
            else:
                st.success(f"✅ 当前持股数 {top_n}，将从 {max_n} 只中择优选取，权重调整会显著影响持仓。")
        st.caption(f"当前股票池共 {max_n} 只，每期将从中选出 {top_n} 只持有。")

        # 因子权重设置（折叠面板内）
        with st.expander("⚙️ 因子权重设置 (高级)", expanded=st.session_state.expand_weights):
                        # ---------- 权重调整思路引导 ----------
            with st.expander("💡 调整权重没方向？点我看思路", expanded=False):
                st.markdown("""
                **跑输基准后，怎么调权重？**  
                不用急，每次只改一个因子，幅度可以大一点（比如翻倍），观察变化。

                **大方向思考：**
                - 🧩 **持股数是不是太小？** → 太少容易运气差，适当增加（如2只→5只）。
                - 📈 **市场风格偏大盘还是小盘？** → 加大低波动、大市值因子的权重，贴近市场风格。
                - 🏭 **持仓是否过度集中在某个行业？** → 降低让你集中的因子，增加分散类因子（如反转、波动率）。
                - 🐂 **单边牛市却频繁换仓？** → 降低短期因子（反转、短期动量），提高中长期因子（新动量）。
                - 🐻 **震荡市一直亏？** → 降低趋势因子，增加反转、低波动因子。
                - ⚠️ **PE/PB因子没生效？** → 检查数据缺失提示，缺失太多就暂时关闭基本面因子。

                **最简单调试循环：**
                1. 固定持股数（如5只），跑一次基准。
                2. 只改一个因子权重（如“新动量”加倍），再跑一次。
                3. 对比持仓和净值变化。
                4. 无变化？换一个因子试试；波动变大但没多赚？恢复，试另一个方向。
                """)
            # ---------- 引导结束 ----------
            st.markdown("各因子权重之和应为1。权重越大，该因子对选股的影响越大。拖动滑块后点击“开始回测”生效。")
            
            # 因子通俗解释映射
            factor_tips = {
                'momentum': "过去20天涨得多的股票得分高。**适合追涨**。",
                'reversal': "过去5天跌得多的股票得分高。**适合抄底**。",
                'volatility': "波动越小的股票得分越高。**适合求稳**。",
                'rpv': "价量配合好的股票得分高。**放量上涨更可靠**。",
                'new_momentum': "中期趋势强的股票得分高。**看最近两三个月**。",
                'combo': "动量、反转、波动率的平均值。**均衡型**。",
                'pe': "市盈率越低得分越高。**便宜货**。",
                'pb': "市净率越低得分越高。**资产打折**。"
            }
            
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                w_mom = st.number_input("动量", value=0.05, step=0.05, format="%.2f", key="weight_mom",
                                        help=factor_tips['momentum'])
                st.caption(factor_tips['momentum'])
                w_rev = st.number_input("反转", value=0.05, step=0.05, format="%.2f", key="weight_rev",
                                        help=factor_tips['reversal'])
                st.caption(factor_tips['reversal'])
                w_vol = st.number_input("波动率", value=0.10, step=0.05, format="%.2f", key="weight_vol",
                                        help=factor_tips['volatility'])
                st.caption(factor_tips['volatility'])
                w_rpv = st.number_input("RPV (价量相关)", value=0.30, step=0.05, format="%.2f", key="weight_rpv",
                                        help=factor_tips['rpv'])
                st.caption(factor_tips['rpv'])
            with col_w2:
                w_newmom = st.number_input("新动量", value=0.30, step=0.05, format="%.2f", key="weight_newmom",
                                           help=factor_tips['new_momentum'])
                st.caption(factor_tips['new_momentum'])
                w_combo = st.number_input("综合量价", value=0.20, step=0.05, format="%.2f", key="weight_combo",
                                          help=factor_tips['combo'])
                st.caption(factor_tips['combo'])
            
            current_weights = {
                'momentum': w_mom,
                'reversal': w_rev,
                'volatility': w_vol,
                'rpv': w_rpv,
                'new_momentum': w_newmom,
                'combo': w_combo,
            }
            
            # 归一化显示
            weight_sum = sum(current_weights.values())
            if weight_sum > 0:
                normalized = {k: v/weight_sum for k, v in current_weights.items()}
                norm_text = " | ".join([f"{FACTOR_NAME_CN[k]}: {v*100:.0f}%" for k, v in normalized.items()])
                st.info(f"📐 归一化后实际权重（百分比）：{norm_text}")
            else:
                st.warning("所有因子权重为0，将自动使用等权。")
            
            # 基本面因子
            # 检测Tushare是否可用
            from data.fundamental import pro as ts_pro
            tushare_ok = ts_pro is not None
            use_fundamental = st.checkbox(
                "加入基本面因子 (PE, PB)",
                value=False,
                key="use_fundamental",
                disabled=not tushare_ok,
                help="需要Tushare数据源，勾选前请确保已配置TUSHARE_TOKEN"
            )
            if not tushare_ok:
                st.error("⚠️ Tushare未连接，PE/PB数据无法获取。请配置TUSHARE_TOKEN环境变量后重启应用。")
            else:
                st.success("✅ Tushare已连接，PE/PB数据可用。")
            
            if use_fundamental:
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    w_pe = st.number_input("PE", value=0.10, step=0.05, format="%.2f", key="weight_pe",
                                           help=factor_tips['pe'])
                    st.caption(factor_tips['pe'])
                with col_f2:
                    w_pb = st.number_input("PB", value=0.10, step=0.05, format="%.2f", key="weight_pb",
                                           help=factor_tips['pb'])
                    st.caption(factor_tips['pb'])
                current_weights['pe'] = w_pe
                current_weights['pb'] = w_pb
                # 重新计算归一化显示（包含PE/PB）
                weight_sum2 = sum(current_weights.values())
                if weight_sum2 > 0:
                    normalized2 = {k: v/weight_sum2 for k, v in current_weights.items()}
                    norm_text2 = " | ".join([f"{FACTOR_NAME_CN.get(k, k)}: {v*100:.0f}%" for k, v in normalized2.items()])
                    st.info(f"📐 加入基本面后归一化权重：{norm_text2}")
        
        commission = st.number_input("手续费率", value=0.0005, format="%.4f", help="单边万分之五")
        st.caption("实盘建议设置0.05%~0.2%（0.0005~0.002）")
        slippage = st.number_input("滑点", value=0.0005, format="%.4f", help="万分之五")
        st.caption("因流动性导致的成交价差，实盘建议0.05%~0.1%（0.0005~0.001）")
        
        submitted = st.form_submit_button("🚀 开始组合回测", type="primary")
    
    if submitted:
        if len(final_stock_list) < 2:
            st.error("请至少选择2只股票并确认股票列表。")
            st.stop()
        
        with st.spinner("正在运行多因子回测，请稍候..."):
            try:
                nav, bench, holdings, metrics, factors_history = portfolio_backtest(
                    start_date=start_date.strftime('%Y%m%d'),
                    end_date=end_date.strftime('%Y%m%d'),
                    stock_list=final_stock_list,
                    top_n=top_n,
                    rebalance_freq=rebalance_freq_code,
                    factor_weights=current_weights,
                    commission=commission,
                    slippage=slippage
                )
            except Exception as e:
                st.error(f"回测失败: {e}")
                st.stop()

        # 展示绩效指标
        st.subheader("📊 组合回测绩效")
        col1, col2, col3 = st.columns(3)
        ann_ret = metrics.get('年化收益率（策略）', 0)
        sharpe = metrics.get('夏普比率', 0)
        max_dd = metrics.get('最大回撤', 0)
        col1.metric("年化收益率", f"{ann_ret*100:.2f}%")
        col2.metric("夏普比率", f"{sharpe:.2f}")
        col3.metric("最大回撤", f"{max_dd*100:.2f}%")
        # 指标解释
        ret_judge = "优秀 👍" if ann_ret > 0.15 else ("良好 ✅" if ann_ret > 0.05 else ("一般 💡" if ann_ret > 0 else "亏损 ⚠️"))
        sharpe_judge = "优秀 👍" if sharpe > 1.5 else ("良好 ✅" if sharpe > 0.8 else "偏低 ⚠️")
        dd_judge = "风险小 👍" if max_dd > -0.1 else ("中等 ✅" if max_dd > -0.2 else "回撤较大 ⚠️")
        st.caption(f"年化收益率 {ret_judge} | 夏普比率 {sharpe_judge} | 最大回撤 {dd_judge}")
        bench_ret = metrics.get('年化收益率（基准）', 0)
        st.caption(f"📈 基准（沪深300）年化收益率：{bench_ret*100:.2f}%")
        
        # 估值缺失提示
        missing_val = metrics.get('估值数据缺失股数', 0)
        if missing_val > 0:
            st.warning(f"⚠️ 有 {missing_val} 只股票缺少估值数据（PE/PB），**你设置的PE/PB因子对它们未生效**。\n"
                       "建议检查股票代码或Tushare权限，或暂时取消基本面因子。")

        st.subheader("💰 资金曲线对比")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=nav.index, y=nav, mode='lines', name='策略净值'))
        fig.add_trace(go.Scatter(x=bench.index, y=bench, mode='lines', name='沪深300基准', line=dict(dash='dash')))
        fig.update_layout(title='策略净值 vs 基准', xaxis_title='日期', yaxis_title='累计净值', hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)

        # 调仓记录
        with st.expander("📋 调仓记录 (前5次)"):
            for i, (date, stocks) in enumerate(holdings.items()):
                if i >= 5:
                    break
                st.write(f"{date.date()}: {stocks[:5]}{'...' if len(stocks)>5 else ''}")

        # 因子明细
        if factors_history:
            with st.expander("📊 调仓因子明细 (每期所选股票的因子值)", expanded=False):
                dates = [d.date() for d, _ in factors_history]
                selected_idx = st.selectbox("选择调仓日期", range(len(dates)), format_func=lambda i: str(dates[i]))
                selected_date, factor_df = factors_history[selected_idx]
                st.caption(f"因子值基于 **{selected_date.date()}** 的数据，已标准化（去极值、Z-score）。")
                factor_df = factor_df.rename(columns=FACTOR_NAME_CN)
                display_df = factor_df.round(4).fillna('-')
                st.dataframe(display_df, use_container_width=True)
        else:
            st.info("无因子数据记录")

        st.session_state.expand_weights = False
        st.success("回测完成！")
    # ================== 智能分析 ==================
# ================== 智能分析 ==================
# ================== 智能分析 ==================
# ================== 智能分析 ==================
with tab3:
    st.header("🧠 智能深度分析")
    st.markdown("利用大模型整合新闻、公告、资金流向等多源信息，给出趋势判断和逻辑链。")

    # 初始化 session_state 用于联动
    if 'ai_symbol_input' not in st.session_state:
        st.session_state.ai_symbol_input = '600519'
    if 'ai_name_input' not in st.session_state:
        st.session_state.ai_name_input = '贵州茅台'

    # ----- 热门股票快捷选择 -----
    st.subheader("🔥 热门股票")
    popular = {
        "寒武纪": "688256", "澜起科技": "688008", "中际旭创": "300308", "海光信息": "688041",
        "宁德时代": "300750", "贵州茅台": "600519", "紫金矿业": "601899",
        "达实智能": "002421", "京能电力": "600578", "天孚通信": "300502",
    }
    cols = st.columns(5)
    for i, (name, code) in enumerate(popular.items()):
        with cols[i % 5]:
            if st.button(name, key=f"ai_pop_{code}"):
                st.session_state.ai_symbol_input = code
                st.session_state.ai_name_input = name
                st.rerun()

    st.markdown("---")

    # ----- 输入区域 -----
    col1, col2 = st.columns([2, 2])
    with col1:
        # 代码输入，on_change 回调用于自动查询名称
        def update_name():
            code = st.session_state.ai_symbol_input.strip()
            if len(code) == 6 and code.isdigit():
                from intelligence.data_sources import get_stock_name
                name = get_stock_name(code)
                if name:
                    st.session_state.ai_name_input = name

        symbol_ai = st.text_input(
            "股票代码",
            key="ai_symbol_input",
            help="输入6位股票代码，自动查询名称",
            on_change=update_name
        )
    with col2:
        stock_name_input = st.text_input(
            "股票名称",
            key="ai_name_input",
            help="可手动修改"
        )

    col_model, _ = st.columns([2, 2])
    with col_model:
        model_choice = st.selectbox(
            "选择模型",
            ["deepseek", "qwen", "ollama"],
            help="deepseek / qwen 需配置 API Key；ollama 需本地启动服务 (使用 gemma3:4b)"
        )

    if st.button("🔍 开始智能分析", key="ai_btn"):
        if not symbol_ai:
            st.warning("请输入股票代码")
        else:
            with st.spinner("正在获取数据并调用大模型分析，约需5-10秒..."):
                result = analyze_stock(symbol_ai, stock_name_input, model=model_choice)

            if 'error' in result:
                st.error(f"分析失败：{result['error']}。请检查 API Key 是否正确配置，或尝试使用本地 ollama 模型。")
                if 'raw_output' in result:
                    with st.expander("📁 模型原始输出（调试用）"):
                        st.text(result['raw_output'])
            else:
                # 显示实际使用的模型
                if result.get('fallback'):
                    st.info(f"ℹ️ 首选模型不可用，已自动切换至备用模型：{result['used_model']}")
                else:
                    st.success(f"✅ 当前使用模型：{result['used_model']}")

                # 趋势仪表盘
                st.subheader("📈 趋势判断")
                score = result.get('score', 0.5)
                trend = result.get('trend', '未知')
                confidence = result.get('confidence', 0)
                st.progress(score, text=f"多头倾向 {score*100:.0f}%")
                col1, col2, col3 = st.columns(3)
                col1.metric("综合判断", trend)
                col2.metric("置信度", f"{confidence*100:.0f}%")
                col3.metric("多头得分", f"{score:.2f}")

                # 逻辑链
                st.subheader("🧩 影响逻辑")
                for item in result.get('logic_chain', []):
                    impact = item.get('impact', '')
                    if '+' in impact:
                        sign = "📈"
                    elif '-' in impact:
                        sign = "📉"
                    else:
                        sign = "➖"
                    st.markdown(f"- {sign} **{item['event']}** ({impact})：{item['reason']}")

                # 风险提示
                risks = result.get('key_risks', [])
                if risks:
                    st.subheader("⚠️ 主要风险")
                    for risk in risks:
                        st.warning(risk)

                # 原始数据展示
                if 'raw_data' in result and result['raw_data']:
                    with st.expander("📁 查看传给模型的原始数据"):
                        rd = result['raw_data']
                        st.markdown("**基本面数据**")
                        st.text(rd.get('fundamentals', '无'))
                        st.markdown("**最近一个月新闻标题**")
                        st.text(rd.get('news_titles', '无'))
                        st.markdown("**最近一个月公告标题**")
                        st.text(rd.get('announcements_titles', '无'))
                        st.markdown("**所属概念板块**")
                        st.write(rd.get('concepts', []))
                        st.markdown("**近期资金流向**")
                        st.text(rd.get('moneyflow', '无'))

                # 原始 JSON（调试用）
                with st.expander("📁 分析结果原始 JSON"):
                    st.json(result)

    st.info("💡 提示：智能分析基于公开信息和 LLM 推理，不构成投资建议。")