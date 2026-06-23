# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import tushare as ts

# ---- 导入 ----
from pages.config_page import show as config_show
from pages.result_page import show as result_show
from backtest.portfolio_backtest import portfolio_backtest
from utils.stock_pool import get_predefined_pool
from config import FACTOR_NAME_CN
from intelligence.analyzer import analyze_stock

st.set_page_config(layout="wide", page_title="MiniQuant 量化分析平台", page_icon="📈")

# 初始化 session_state
if 'page' not in st.session_state:
    st.session_state.page = 'config'

@st.cache_data
def get_all_a_stocks():
    import os
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

# 选项卡
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

    with st.expander("📚 使用帮助（点击展开）", expanded=False):
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
        """)

    # ---------- 1. 股票池选择 ----------
    if 'confirmed_stocks' not in st.session_state:
        st.session_state.confirmed_stocks = []
    if 'manual_stocks' not in st.session_state:
        st.session_state.manual_stocks = []

    col_pool, _ = st.columns([3, 1])
    with col_pool:
        stock_pool_option = st.radio("股票池", ["demo (50只龙头)", "沪深300 (需动态获取)"], horizontal=True, index=0)
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
        st.caption("💡 至少选择2只股票，建议数量大于每期持股数")

    # 手动添加股票
    st.markdown("### 或手动添加股票")
    manual_input = st.text_area("输入股票代码（用逗号、空格或换行分隔）", help="例如：600519,000858,601318")
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

    if st.button("✅ 确认股票列表", use_container_width=True):
        final_list = list(set(selected_from_pool + st.session_state.manual_stocks))
        if len(final_list) < 2:
            st.warning("至少需要选择2只股票才能进行组合回测。")
        else:
            st.session_state.confirmed_stocks = final_list
            # 重置权重
            weight_keys = [
                "weight_mom", "weight_rev", "weight_vol", "weight_rpv",
                "weight_newmom", "weight_combo", "weight_pe", "weight_pb"
            ]
            for key in weight_keys:
                if key in st.session_state:
                    del st.session_state[key]
            if "use_fundamental" in st.session_state:
                del st.session_state["use_fundamental"]
            if 'backtest_result' in st.session_state:
                del st.session_state.backtest_result
            st.session_state.expand_weights = True
            st.success(f"已确认 {len(final_list)} 只股票，权重已重置。")
            st.rerun()

    final_stock_list = st.session_state.confirmed_stocks
    if final_stock_list:
        with st.expander(f"📋 当前股票列表（共{len(final_stock_list)}只）", expanded=True):
            st.write(final_stock_list)
            if len(final_stock_list) < 2:
                st.warning("⚠️ 当前股票数量少于2只，无法进行组合回测。")
    else:
        st.info("尚未选择股票，请从上方选择或手动添加。")

    # ---------- 2. 回测参数与权重设置 ----------
    st.markdown("---")
    st.subheader("⚙️ 回测参数与因子权重")

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
            st.toast("✅ 权重已重置为默认值")
            st.session_state.expand_weights = True
            st.rerun()

    if 'expand_weights' not in st.session_state:
        st.session_state.expand_weights = False

    with st.form("portfolio_form"):
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("回测开始日期", value=pd.to_datetime("2022-01-01"))
        with col2:
            end_date = st.date_input("回测结束日期", value=pd.to_datetime("2024-12-31"))
        rebalance_freq = st.radio("调仓频率", ["每月", "每季度"], horizontal=True, index=0)
        freq_map = {"每月": "M", "每季度": "Q"}
        rebalance_freq_code = freq_map[rebalance_freq]

        max_n = len(final_stock_list)
        if max_n < 2:
            st.warning("请先确认至少2只股票")
            top_n = 1
        else:
            default_top_n = min(5, max_n-1) if max_n > 2 else 1
            top_n = st.slider(
                "📌 每期持有几只股票？",
                min_value=1, max_value=max_n,
                value=max(1, default_top_n), step=1,
                help="选股数小于池子大小时，权重调整才会影响结果。"
            )
            if top_n == max_n:
                st.error(f"⚠️ 持股数等于池子大小 ({max_n})，因子权重调整不会改变持仓。")
            elif top_n >= max_n * 0.8:
                st.warning(f"💡 持股数接近池子大小，权重变化对持仓影响较小。")
            else:
                st.success(f"✅ 当前持股数 {top_n}，权重调整将显著影响持仓。")
        st.caption(f"当前股票池共 {max_n} 只，每期将从中选出 {top_n} 只持有。")

        with st.expander("⚙️ 因子权重设置 (高级)", expanded=st.session_state.expand_weights):
            with st.expander("💡 调整权重没方向？点我看思路", expanded=False):
                st.markdown("""......""")  # 保留思路提示
            st.markdown("各因子权重之和应为1。拖动滑块后点击“开始回测”生效。")
            factor_tips = {
                'momentum': "过去20天涨得多的股票得分高。适合追涨。",
                'reversal': "过去5天跌得多的股票得分高。适合抄底。",
                'volatility': "波动越小得分越高。适合求稳。",
                'rpv': "价量配合越好得分越高。放量上涨更可靠。",
                'new_momentum': "中期趋势强的股票得分高。看最近两三个月。",
                'combo': "动量、反转、波动率的平均。均衡型。",
                'pe': "市盈率越低得分越高。便宜货。",
                'pb': "市净率越低得分越高。资产打折。"
            }
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                w_mom = st.number_input("动量", value=0.05, step=0.05, format="%.2f", key="weight_mom", help=factor_tips['momentum'])
                st.caption(factor_tips['momentum'])
                w_rev = st.number_input("反转", value=0.05, step=0.05, format="%.2f", key="weight_rev", help=factor_tips['reversal'])
                st.caption(factor_tips['reversal'])
                w_vol = st.number_input("波动率", value=0.10, step=0.05, format="%.2f", key="weight_vol", help=factor_tips['volatility'])
                st.caption(factor_tips['volatility'])
                w_rpv = st.number_input("RPV (价量相关)", value=0.30, step=0.05, format="%.2f", key="weight_rpv", help=factor_tips['rpv'])
                st.caption(factor_tips['rpv'])
            with col_w2:
                w_newmom = st.number_input("新动量", value=0.30, step=0.05, format="%.2f", key="weight_newmom", help=factor_tips['new_momentum'])
                st.caption(factor_tips['new_momentum'])
                w_combo = st.number_input("综合量价", value=0.20, step=0.05, format="%.2f", key="weight_combo", help=factor_tips['combo'])
                st.caption(factor_tips['combo'])

            current_weights = {
                'momentum': w_mom, 'reversal': w_rev, 'volatility': w_vol,
                'rpv': w_rpv, 'new_momentum': w_newmom, 'combo': w_combo,
            }

            weight_sum = sum(current_weights.values())
            if weight_sum > 0:
                normalized = {k: v/weight_sum for k, v in current_weights.items()}
                norm_text = " | ".join([f"{FACTOR_NAME_CN.get(k, k)}: {v*100:.0f}%" for k, v in normalized.items()])
                st.info(f"📐 归一化后实际权重：{norm_text}")
            else:
                st.warning("所有权重为0，将自动使用等权。")

            from data.fundamental import pro as ts_pro
            tushare_ok = ts_pro is not None
            use_fundamental = st.checkbox("加入基本面因子 (PE, PB)", value=False, key="use_fundamental", disabled=not tushare_ok)
            if not tushare_ok:
                st.error("⚠️ Tushare未连接，PE/PB数据无法获取。")
            else:
                st.success("✅ Tushare已连接，PE/PB数据可用。")

            if use_fundamental:
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    w_pe = st.number_input("PE", value=0.10, step=0.05, format="%.2f", key="weight_pe", help=factor_tips['pe'])
                    st.caption(factor_tips['pe'])
                with col_f2:
                    w_pb = st.number_input("PB", value=0.10, step=0.05, format="%.2f", key="weight_pb", help=factor_tips['pb'])
                    st.caption(factor_tips['pb'])
                current_weights['pe'] = w_pe
                current_weights['pb'] = w_pb

        commission = st.number_input("手续费率", value=0.0005, format="%.4f")
        slippage = st.number_input("滑点", value=0.0005, format="%.4f")
        submitted = st.form_submit_button("🚀 开始组合回测", type="primary")

    if submitted:
        if len(final_stock_list) < 2:
            st.error("请至少选择2只股票并确认股票列表。")
            st.stop()

        with st.spinner("正在运行多因子回测，请稍候..."):
            try:
                nav, bench, holdings, metrics, factors_history, holdings_detail = portfolio_backtest(
                    start_date=start_date.strftime('%Y%m%d'),
                    end_date=end_date.strftime('%Y%m%d'),
                    stock_list=final_stock_list,
                    top_n=top_n,
                    rebalance_freq=rebalance_freq_code,
                    factor_weights=current_weights,
                    commission=commission,
                    slippage=slippage
                )
                st.session_state.backtest_result = {
                    'nav': nav, 'bench': bench, 'holdings': holdings,
                    'metrics': metrics, 'factors_history': factors_history,
                    'holdings_detail': holdings_detail, 'used_weights': current_weights,
                    'top_n': top_n, 'commission': commission, 'slippage': slippage
                }
            except Exception as e:
                st.error(f"回测失败: {e}")
                st.stop()

    if 'backtest_result' in st.session_state:
        res = st.session_state.backtest_result
        nav = res['nav']
        bench = res['bench']
        holdings = res['holdings']
        metrics = res['metrics']
        factors_history = res['factors_history']
        holdings_detail = res['holdings_detail']
        current_weights = res['used_weights']

        st.subheader("📊 组合回测绩效")
        col1, col2, col3 = st.columns(3)
        ann_ret = metrics.get('年化收益率（策略）', 0)
        sharpe = metrics.get('夏普比率', 0)
        max_dd = metrics.get('最大回撤', 0)
        col1.metric("年化收益率", f"{ann_ret*100:.2f}%")
        col2.metric("夏普比率", f"{sharpe:.2f}")
        col3.metric("最大回撤", f"{max_dd*100:.2f}%")
        bench_ret = metrics.get('年化收益率（基准）', 0)
        st.caption(f"📈 基准（沪深300）年化收益率：{bench_ret*100:.2f}%")

        missing_val = metrics.get('估值数据缺失股数', 0)
        if ('pe' in current_weights or 'pb' in current_weights) and missing_val > 0:
            st.warning(f"⚠️ 有 {missing_val} 只股票缺少估值数据，PE/PB因子未生效。")

        st.subheader("💰 资金曲线对比")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=nav.index, y=nav, mode='lines', name='策略净值'))
        fig.add_trace(go.Scatter(x=bench.index, y=bench, mode='lines', name='沪深300基准', line=dict(dash='dash')))
        fig.update_layout(title='策略净值 vs 基准', xaxis_title='日期', yaxis_title='累计净值', hovermode='x unified')
        st.plotly_chart(fig, width='stretch')

        st.subheader("📋 每期持仓明细")
        if holdings_detail:
            dates = sorted(holdings_detail.keys())
            selected_idx = st.selectbox("选择调仓日期查看持仓", range(len(dates)),
                                        format_func=lambda i: str(dates[i].date()), key="detail_date")
            sel_date = dates[selected_idx]
            detail_df = holdings_detail[sel_date].copy()
            detail_df = detail_df.rename(columns=FACTOR_NAME_CN)
            detail_df['score'] = detail_df['score'].round(4)
            st.dataframe(detail_df, width='stretch')
            st.caption(f"共 {len(detail_df)} 只股票，按综合得分降序排列。")
        else:
            st.info("无持仓明细数据。")

        with st.expander("📋 调仓记录 (前5次，列表形式)", expanded=False):
            for i, (date, stocks) in enumerate(holdings.items()):
                if i >= 5:
                    break
                st.write(f"{date.date()}: {stocks[:5]}{'...' if len(stocks)>5 else ''}")

        if factors_history:
            with st.expander("📊 调仓因子明细 (可查看全部股票得分排名)", expanded=False):
                dates_f = [d.date() for d, _ in factors_history]
                selected_idx_f = st.selectbox("选择调仓日期", range(len(dates_f)),
                                              format_func=lambda i: str(dates_f[i]), key="factor_date")
                sel_date_f, factor_df_all = factors_history[selected_idx_f]
                st.caption(f"因子值基于 **{sel_date_f.date()}** 的数据，已标准化。")
                score = pd.Series(0.0, index=factor_df_all.index)
                for col, w in current_weights.items():
                    if col in factor_df_all.columns:
                        score += factor_df_all[col] * w
                factor_df_all = factor_df_all.copy()
                factor_df_all['score'] = score
                factor_df_all['rank'] = score.rank(ascending=False).astype(int)
                show_all = st.checkbox("显示全部股票（默认只显示当期持仓）", value=False)
                if not show_all:
                    held = holdings.get(pd.to_datetime(sel_date_f), [])
                    factor_df_show = factor_df_all.loc[factor_df_all.index.isin(held)].sort_values('score', ascending=False)
                else:
                    factor_df_show = factor_df_all.sort_values('score', ascending=False)
                factor_df_show = factor_df_show.rename(columns=FACTOR_NAME_CN)
                st.dataframe(factor_df_show.style.format("{:.4f}"), width='stretch')
        else:
            st.info("无因子数据记录")

        st.session_state.expand_weights = False
        st.success("回测完成！")

# ================== 智能分析 ==================
with tab3:
    st.header("🧠 智能深度分析")
    st.markdown("结合付费新闻源(Finnhub/NewsAPI)、量化快照与大模型，给出趋势判断和逻辑链。")

    if 'ai_symbol_input' not in st.session_state:
        st.session_state.ai_symbol_input = '600519'
    if 'ai_name_input' not in st.session_state:
        st.session_state.ai_name_input = '贵州茅台'

    # A股热门（折叠）
    with st.expander("🇨🇳 A股热门（点击展开）", expanded=False):
        a_stocks = [
            ("贵州茅台", "600519"), ("宁德时代", "300750"), ("比亚迪", "002594"),
            ("五粮液", "000858"), ("隆基绿能", "601012"), ("药明康德", "603259"),
            ("中芯国际", "688981"), ("招商银行", "600036"), ("中国平安", "601318"),
            ("美的集团", "000333"), ("长江电力", "600900"), ("恒瑞医药", "600276"),
            ("海光信息", "688041"), ("中际旭创", "300308"), ("北方华创", "002371"),
            ("紫金矿业", "601899"), ("立讯精密", "002475"), ("迈瑞医疗", "300760"),
            ("阳光电源", "300274"), ("泸州老窖", "000568")
        ]
        cols_a = st.columns(5)
        for i, (name, code) in enumerate(a_stocks):
            with cols_a[i % 5]:
                if st.button(name, key=f"a_{code}"):
                    st.session_state.ai_symbol_input = code
                    st.session_state.ai_name_input = name
                    st.rerun()

    # 美股热门（折叠）
    with st.expander("🇺🇸 美股热门（点击展开）", expanded=False):
        us_stocks = [
            ("苹果", "AAPL"), ("微软", "MSFT"), ("谷歌", "GOOGL"),
            ("亚马逊", "AMZN"), ("英伟达", "NVDA"), ("特斯拉", "TSLA"),
            ("Meta", "META"), ("台积电", "TSM"), ("阿里巴巴", "BABA"),
            ("拼多多", "PDD"), ("网易", "NTES"), ("京东", "JD"),
            ("百度", "BIDU"), ("蔚来", "NIO"), ("理想汽车", "LI"),
            ("小鹏汽车", "XPEV"), ("Palantir", "PLTR"), ("AMD", "AMD"),
            ("可口可乐", "KO"), ("迪士尼", "DIS")
        ]
        cols_us = st.columns(5)
        for i, (name, code) in enumerate(us_stocks):
            with cols_us[i % 5]:
                if st.button(name, key=f"us_{code}"):
                    st.session_state.ai_symbol_input = code
                    st.session_state.ai_name_input = name
                    st.rerun()

    st.markdown("---")
    col1, col2 = st.columns([2, 2])
    with col1:
        def update_name():
            code = st.session_state.ai_symbol_input.strip()
            if len(code) == 6 and code.isdigit():
                from intelligence.data_sources import get_stock_name
                name = get_stock_name(code)
                if name:
                    st.session_state.ai_name_input = name
        symbol_ai = st.text_input("股票代码", key="ai_symbol_input", on_change=update_name)
    with col2:
        stock_name_input = st.text_input("股票名称", key="ai_name_input")

    col_model, _ = st.columns([2, 2])
    with col_model:
        model_choice = st.radio("选择模型", ["deepseek", "qwen", "ollama"], horizontal=True,
                                help="deepseek/qwen 需API Key，ollama 需本地启动服务")

    with st.expander("📝 手动补充最新消息（可选）", expanded=False):
        manual_news = st.text_area("在这里输入你看到的重要新闻、公告或政策变化，每行一条",
                                   key="manual_news", height=100,
                                   help="例如：公司发布业绩预告，净利润同比增长50%")

    if st.button("🔍 开始智能分析", key="ai_btn"):
        if not symbol_ai:
            st.warning("请输入股票代码")
        else:
            with st.spinner("正在获取多源信息并分析，约需5-10秒..."):
                result = analyze_stock(symbol_ai, stock_name_input, model=model_choice, manual_news=manual_news)

            if 'error' in result:
                st.error(f"分析失败：{result['error']}")
            else:
                if result.get('fallback'):
                    st.info(f"ℹ️ 首选模型不可用，已自动切换至备用模型：{result['used_model']}")
                else:
                    st.success(f"✅ 当前使用模型：{result['used_model']}")

                rd = result.get('raw_data', {})
                # 量化快照+行业背景 合并为一行
                snap = rd.get('quant_snapshot', '')
                bg = rd.get('industry_bg', '')
                if snap or bg:
                    st.caption(f"📊 {snap} | 🏭 {bg}")

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
                    sign = "📈" if '+' in impact else "📉" if '-' in impact else "➖"
                    st.markdown(f"- {sign} **{item['event']}** ({impact})：{item['reason']}")

                # 风险提示
                risks = result.get('key_risks', [])
                if risks:
                    st.subheader("⚠️ 主要风险")
                    for risk in risks:
                        st.warning(risk)

                # 数据来源（折叠）
                news_df = rd.get('news_df')
                with st.expander("📋 数据来源（点击展开）", expanded=False):
                    if news_df is not None and not news_df.empty:
                        source_counts = news_df['source'].value_counts().to_dict()
                        source_str = "、".join([f"{s}({c}条)" for s, c in source_counts.items()])
                        st.caption(f"共获取 {len(news_df)} 条信息，来源：{source_str}")
                        st.markdown("**最新动态：**")
                        for _, row in news_df.head(5).iterrows():
                            title = row['title']
                            source = row['source']
                            content = row.get('content', '')
                            detail = f" — {content[:80]}..." if content else ""
                            st.markdown(f"- [{source}] {title}{detail}")
                    else:
                        st.warning("自动获取信息较少，建议手动补充最新消息。")

                # 技术细节（折叠）
                with st.expander("🔧 技术细节（调试用）", expanded=False):
                    st.markdown("**基本面数据**")
                    st.text(rd.get('fundamentals', '无'))
                    st.markdown("**所有新闻/公告列表**")
                    if news_df is not None and not news_df.empty:
                        st.dataframe(news_df[['source', 'title', 'content']], width='stretch')
                    else:
                        st.text("无")
                    st.markdown("**模型实际接收的新闻文本（完整）**")
                    news_full_text = "\n".join([
                        f"[{row['source']}] {row['title']} {row.get('content', '')[:100]}"
                        for _, row in news_df.iterrows()
                    ]) if news_df is not None and not news_df.empty else "无"
                    if manual_news.strip():
                        news_full_text += "\n\n【手动补充】\n" + manual_news
                    st.text_area("新闻文本", value=news_full_text, height=200, disabled=True)
                    st.markdown("**所属概念板块**")
                    st.write(rd.get('concepts', []))
                    st.markdown("**近期资金流向**")
                    st.text(rd.get('moneyflow', '无'))
                    st.caption(rd.get('data_period', ''))
                    st.markdown("**分析结果原始 JSON**")
                    st.json(result)

    st.info("💡 提示：智能分析基于公开信息和 LLM 推理，不构成投资建议。")