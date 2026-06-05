# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import config_page
import result_page
from portfolio_backtest import portfolio_backtest
from stock_pool import get_predefined_pool
from factor_calc import get_all_factors_batch
import tushare as ts

st.set_page_config(layout="wide", page_title="MiniQuant 量化分析平台", page_icon="📈")

# 初始化 session_state
if 'page' not in st.session_state:
    st.session_state.page = 'config'

# 因子名称中英文映射
FACTOR_NAME_CN = {
    'momentum': '动量',
    'reversal': '反转',
    'volatility': '波动率',
    'rpv': '价量相关(RPV)',
    'new_momentum': '新动量',
    'combo': '综合量价',
    'pe': '市盈率(PE)',
    'pb': '市净率(PB)',
}

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
tab1, tab2 = st.tabs(["📈 单股票分析", "📊 多因子组合回测"])

# ================== 单股票分析 ==================
with tab1:
    if st.session_state.page == 'config':
        config_page.show()
    else:
        result_page.show()

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
        stock_pool_option = st.selectbox("股票池", ["demo (10只龙头)", "沪深300 (需动态获取)"], index=0,
                                         help="demo池为10只行业龙头，沪深300需动态获取（耗时较长）")
        if stock_pool_option == "demo (10只龙头)":
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
    
    # 确认股票列表
    if st.button("✅ 确认股票列表", use_container_width=True):
        final_list = list(set(selected_from_pool + st.session_state.manual_stocks))
        if len(final_list) < 2:
            st.warning("至少需要选择2只股票才能进行组合回测。")
        else:
            st.session_state.confirmed_stocks = final_list
            st.success(f"已确认 {len(final_list)} 只股票")
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

    # ---------- 2. 回测参数设置与权重调整（全部放在一个表单内，权重使用默认值）----------
    st.markdown("---")
    st.subheader("⚙️ 回测参数与因子权重")
    
    # 重置默认权重按钮（直接刷新页面）
    if st.button("🔄 重置为默认权重"):
        st.rerun()
    
    # 主表单
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
        
        # 因子权重设置（折叠面板，放在表单内，使用固定默认值）
        with st.expander("⚙️ 因子权重设置 (高级)", expanded=False):
            st.markdown("各因子权重之和应为1。权重越大，该因子对选股的影响越大。")
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                # 使用固定默认值，不依赖 session_state
                w_mom = st.number_input("动量", value=0.05, step=0.05, format="%.2f")
                st.caption("过去20天涨得多的股票得分高")
                w_rev = st.number_input("反转", value=0.05, step=0.05, format="%.2f")
                st.caption("过去5天跌得多的股票得分高")
                w_vol = st.number_input("波动率", value=0.10, step=0.05, format="%.2f")
                st.caption("波动越小得分越高")
                w_rpv = st.number_input("RPV (价量相关)", value=0.30, step=0.05, format="%.2f")
                st.caption("价量配合越好得分越高")
            with col_w2:
                w_newmom = st.number_input("新动量", value=0.30, step=0.05, format="%.2f")
                st.caption("改进版动量，捕捉中期趋势")
                w_combo = st.number_input("综合量价", value=0.20, step=0.05, format="%.2f")
                st.caption("动量、反转、波动率的平均")
            
            # 构建当前权重字典
            current_weights = {
                'momentum': w_mom,
                'reversal': w_rev,
                'volatility': w_vol,
                'rpv': w_rpv,
                'new_momentum': w_newmom,
                'combo': w_combo,
            }
            
            use_fundamental = st.checkbox("加入基本面因子 (PE, PB)", value=False)
            if use_fundamental:
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    w_pe = st.number_input("PE", value=0.10, step=0.05, format="%.2f")
                    st.caption("市盈率越低越好")
                with col_f2:
                    w_pb = st.number_input("PB", value=0.10, step=0.05, format="%.2f")
                    st.caption("市净率越低越好")
                current_weights['pe'] = w_pe
                current_weights['pb'] = w_pb
        
        # 手续费和滑点
        commission = st.number_input("手续费率", value=0.0005, format="%.4f", help="单边万分之五")
        st.caption("实盘建议设置0.05%~0.2%")
        slippage = st.number_input("滑点", value=0.0005, format="%.4f", help="万分之五")
        st.caption("因流动性导致的成交价差")
        
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
                    top_n=15,
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
        col1.metric("年化收益率", f"{metrics.get('年化收益率（策略）',0)*100:.2f}%")
        col2.metric("夏普比率", f"{metrics.get('夏普比率',0):.2f}")
        col3.metric("最大回撤", f"{metrics.get('最大回撤',0)*100:.2f}%")
        st.caption(f"基准（沪深300）年化收益率：{metrics.get('年化收益率（基准）',0)*100:.2f}%")

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
                # 重命名为中文
                factor_df = factor_df.rename(columns=FACTOR_NAME_CN)
                display_df = factor_df.round(4).fillna('-')
                st.dataframe(display_df, use_container_width=True)
        else:
            st.info("无因子数据记录")

        st.success("回测完成！")