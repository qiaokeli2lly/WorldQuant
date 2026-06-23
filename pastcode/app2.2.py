import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from data_utils import get_stock_data
from indicators import compute_all_indicators
from backtest import run_backtest, calculate_metrics, multi_strategy_backtest, grid_search_ma
from strategies import ma_strategy, rsi_strategy, bollinger_strategy
from plot_charts import plot_equity_curve
from fundamental import get_fundamental

st.set_page_config(layout="wide", page_title="MiniQuant 量化分析平台", page_icon="📈")

# ================== 辅助绘图函数（增强悬停、休市提示）==================
def plot_candlestick_with_indicators(df, ma_periods, bb_period, bb_std, show_candlestick):
    df = df.copy()
    df['is_trading_day'] = (df['volume'] > 0) & (df['return'].notna())
    plot_df = df.copy()
    if show_candlestick:
        for col in ['open', 'high', 'low', 'close']:
            plot_df.loc[~plot_df['is_trading_day'], col] = np.nan

    fig = make_subplots(rows=1, cols=1)
    if show_candlestick:
        hint_text = ['⚠️ 非交易日（前值填充）<br>' if not td else '' for td in plot_df['is_trading_day']]
        customdata = np.column_stack((
            plot_df['open'].values, plot_df['high'].values, plot_df['low'].values,
            plot_df['close'].values, plot_df['volume'].values, hint_text
        ))
        fig.add_trace(go.Candlestick(
            x=plot_df.index, open=plot_df['open'], high=plot_df['high'],
            low=plot_df['low'], close=plot_df['close'], name='K线',
            hovertemplate='<b>%{x}</b><br>%{customdata[5]}'
                          '开盘: %{customdata[0]:.2f}<br>最高: %{customdata[1]:.2f}<br>'
                          '最低: %{customdata[2]:.2f}<br>收盘: %{customdata[3]:.2f}<br>'
                          '成交量: %{customdata[4]:.0f} 手<extra></extra>',
            customdata=customdata
        ))
    else:
        hint_text = ['⚠️ 非交易日<br>' if not td else '' for td in df['is_trading_day']]
        customdata = np.column_stack((df['volume'].values, hint_text))
        fig.add_trace(go.Scatter(
            x=df.index, y=df['close'], mode='lines', name='收盘价',
            line=dict(color='black', width=1.5),
            hovertemplate='<b>%{x}</b><br>%{customdata[1]}收盘价: %{y:.2f}<br>成交量: %{customdata[0]:.0f} 手<extra></extra>',
            customdata=customdata
        ))
    colors = ['blue', 'orange', 'red', 'green', 'purple']
    for i, p in enumerate(ma_periods):
        col = f'MA{p}'
        if col in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df[col], mode='lines', name=col,
                                     line=dict(color=colors[i % len(colors)], width=1)))
    if 'BB_upper' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_upper'], mode='lines', name='BB上轨',
                                 line=dict(color='gray', dash='dash')))
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_lower'], mode='lines', name='BB下轨',
                                 line=dict(color='gray', dash='dash')))
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_mid'], mode='lines', name='BB中轨',
                                 line=dict(color='gray', width=1)))
    fig.update_layout(title='价格走势', xaxis_title='日期', yaxis_title='价格', height=500,
                      hovermode='x unified', hoverlabel=dict(bgcolor="white", font_size=12),
                      xaxis=dict(tickformat='%Y-%m-%d', tickangle=45))
    return fig

def plot_rsi(df, period, overbought, oversold):
    col = f'RSI_{period}'
    fig = go.Figure()
    if col in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df[col], mode='lines', name='RSI', line=dict(color='purple', width=1.5)))
        fig.add_hline(y=overbought, line_dash="dash", line_color="red", annotation_text=f"超买({overbought})")
        fig.add_hline(y=oversold, line_dash="dash", line_color="green", annotation_text=f"超卖({oversold})")
        fig.update_layout(yaxis_range=[0,100], title=f'RSI({period})', hovermode='x unified',
                          xaxis=dict(tickformat='%Y-%m-%d', tickangle=45))
    return fig

def plot_macd(df):
    fig = go.Figure()
    if 'MACD' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], mode='lines', name='MACD', line=dict(color='blue')))
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_signal'], mode='lines', name='Signal', line=dict(color='red')))
        fig.add_bar(x=df.index, y=df['MACD_hist'], name='Histogram', marker_color='gray')
        fig.update_layout(title='MACD', hovermode='x unified', xaxis=dict(tickformat='%Y-%m-%d', tickangle=45))
    return fig

def plot_kdj(df):
    fig = go.Figure()
    if 'K' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['K'], mode='lines', name='K', line=dict(color='blue')))
        fig.add_trace(go.Scatter(x=df.index, y=df['D'], mode='lines', name='D', line=dict(color='orange')))
        fig.add_trace(go.Scatter(x=df.index, y=df['J'], mode='lines', name='J', line=dict(color='purple')))
        fig.update_layout(title='KDJ', hovermode='x unified', xaxis=dict(tickformat='%Y-%m-%d', tickangle=45))
    return fig

# ================== 指标解释函数（用于百科面板）==================
def indicator_glossary():
    st.markdown("""
    ### 📚 指标百科 – 每个指标都在说什么？

    ---
    **1. 基础数据**
    - **开盘价、最高价、最低价、收盘价**：代表一天中股票交易的四个关键价格。收盘价是每日结算基准，最高/最低反映当日波动范围。
    - **成交量**：当天成交的总股数（手）。成交量放大通常意味着市场参与度高，价格变动更可信。
    - **涨跌幅**：（今日收盘-昨日收盘）/昨日收盘，直观反映当日盈亏比例。

    **2. 移动平均线 (MA)**
    - **算法**：过去N日收盘价的算术平均值。
    - **含义**：平滑价格波动，识别趋势方向。短期MA（如5日）对价格反应快，长期MA（如60日）反映主要趋势。金叉（短期上穿长期）看涨，死叉看跌。

    **3. RSI（相对强弱指数）**
    - **算法**：RSI = 100 - 100/(1+RS)，其中RS = 平均上涨幅度/平均下跌幅度（通常14天）。
    - **含义**：衡量股价涨跌的速度和幅度。RSI>70视为超买（可能回调），RSI<30视为超卖（可能反弹）。适合震荡行情。

    **4. 布林带**
    - **算法**：中轨 = MA20，上轨 = 中轨 + k×标准差，下轨 = 中轨 - k×标准差（k常取2）。
    - **含义**：股价通常在上轨和下轨之间波动。触及上轨可能超买，触及下轨可能超卖。带宽收窄预示变盘。

    **5. MACD**
    - **算法**：快线(12日EMA) - 慢线(26日EMA) = DIF，再对DIF做9日EMA得到DEA，柱状图 = DIF - DEA。
    - **含义**：金叉（DIF上穿DEA）买入信号，死叉卖出。柱状图由负转正看涨。

    **6. KDJ**
    - **算法**：基于9日内最高、最低、收盘计算RSV，再平滑得K、D、J。
    - **含义**：K、D值<20超卖，>80超买。金叉买入，死叉卖出。适合短线。

    **7. 成交量比率**
    - **算法**：当前成交量 / 过去20日均量。
    - **含义**：>1表示放量，<1表示缩量。价涨量增是健康趋势。

    **8. 策略信号**
    - **双均线金叉/死叉**：趋势跟踪信号，金叉（短期>长期）买入，死叉卖出。
    - **RSI超卖/超买**：均值回归信号，超卖买入，超买卖出。
    - **布林带触及**：价格触及下轨可能反弹，触及上轨可能回落。
    """)

# ================== 信号解释器 ==================
def explain_signal(row, strategy_type, params):
    """策略信号自然语言解释器"""
    if strategy_type == "双均线":
        short_ma = params['short_ma']
        long_ma = params['long_ma']
        short_val = row.get(f'MA{short_ma}', 0)
        long_val = row.get(f'MA{long_ma}', 0)
        if row['signal'] == 1:
            return f"📢 **买入信号**：{short_ma}日均线 ({short_val:.2f}) 上穿 {long_ma}日均线 ({long_val:.2f})，通常预示上涨趋势启动。"
        elif row['signal'] == -1:
            return f"📢 **卖出信号**：{short_ma}日均线 ({short_val:.2f}) 下穿 {long_ma}日均线 ({long_val:.2f})，可能进入下跌通道。"
    elif strategy_type == "RSI策略":
        period = params['period']
        rsi_val = row.get(f'RSI_{period}', 0)
        if row['signal'] == 1:
            return f"📢 **买入信号**：RSI({period}) = {rsi_val:.1f}，低于超卖线 {params['oversold']}，历史上超卖后反弹概率较大。"
        elif row['signal'] == -1:
            return f"📢 **卖出信号**：RSI({period}) = {rsi_val:.1f}，高于超买线 {params['overbought']}，可能回调。"
    elif strategy_type == "布林带策略":
        if row['signal'] == 1:
            return f"📢 **买入信号**：收盘价 ({row['close']:.2f}) 触及布林带下轨 ({row['BB_lower']:.2f})，可能超卖反弹。"
        elif row['signal'] == -1:
            return f"📢 **卖出信号**：收盘价 ({row['close']:.2f}) 触及布林带上轨 ({row['BB_upper']:.2f})，可能超买回落。"
    return ""

def explain_pe(pe):
    if pe is None:
        return "暂无数据"
    if pe > 50:
        return "市盈率较高，可能高估，需关注成长性是否匹配。"
    elif pe < 10:
        return "市盈率较低，可能存在低估机会，但需排除基本面恶化的股票。"
    else:
        return "市盈率处于合理区间。"

def explain_pb(pb):
    if pb is None:
        return "暂无数据"
    if pb > 5:
        return "市净率较高，市场给予较高资产溢价，需警惕估值泡沫。"
    elif pb < 1:
        return "市净率低于1，可能跌破净资产，存在价值回归机会，需确认资产质量。"
    else:
        return "市净率合理。"

def signal_historical_performance(df, lookforward_days=[1,5,10,20]):
    """统计历史上买入信号后的收益表现"""
    buy_signals = df[df['signal'] == 1].index
    if len(buy_signals) == 0:
        return None
    stats = {}
    for days in lookforward_days:
        rets = []
        for date in buy_signals:
            future_df = df.loc[date:].iloc[1:]
            if len(future_df) >= days:
                cum_ret = (1 + future_df['return'].iloc[:days]).prod() - 1
                rets.append(cum_ret)
        if rets:
            stats[f'后{days}日'] = {'平均收益': np.mean(rets), '胜率': np.mean(np.array(rets)>0)}
    return stats

# ================== 侧边栏 ==================
with st.sidebar:
    st.header("🔧 参数设置")
    
    # 热门股票快速选择
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

    # 股票代码输入
    if 'symbol' not in st.session_state:
        st.session_state['symbol'] = "600519"
    symbol = st.text_input("📈 股票代码", value=st.session_state['symbol'], help="6位数字A股代码").upper()
    st.session_state['symbol'] = symbol

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("📅 开始日期", value=pd.to_datetime("2022-01-01"), help="回测起始日，建议至少1年数据")
    with col2:
        end_date = st.date_input("📅 结束日期", value=pd.to_datetime("2024-12-31"), help="回测结束日")

    st.subheader("📊 技术指标参数")
    ma_periods = st.multiselect("移动平均线周期", options=[5,10,20,30,60,120,250], default=[5,20,60],
                                help="选择要在K线图上显示的均线。短期均线（5、10）反映近一周/两周趋势，长期均线（60、120）反映季度/半年趋势。")
    bb_period = st.slider("布林带周期", 10, 50, 20,
                          help="计算布林带中轨的移动平均周期，常用20。")
    bb_std = st.slider("布林带标准差倍数", 1.0, 3.0, 2.0, step=0.1,
                       help="上下轨与中轨的距离倍数。倍数越大，通道越宽，价格越不容易突破。")
    show_candlestick = st.radio("主图样式", ["K线", "收盘线"], index=0,
                                help="K线显示每日的开、高、低、收；收盘线只显示收盘价连线，更简洁。") == "K线"

    st.subheader("📉 副图指标")
    show_rsi = st.checkbox("RSI", value=True,
                           help="相对强弱指数，衡量股价涨跌速度。值<30超卖（可能反弹），>70超买（可能回调）。")
    show_macd = st.checkbox("MACD", value=False,
                            help="异同移动平均线，由快慢线和柱状图组成。金叉/死叉是常见买卖信号。")
    show_kdj = st.checkbox("KDJ", value=False,
                           help="随机指标，融合了价格波动幅度。K、D、J三线交叉常被用于短线交易。")
    if show_rsi:
        rsi_period = st.slider("RSI周期", 5, 30, 14,
                               help="计算RSI所用的天数。周期越短信号越敏感（假信号多），周期越长信号越平滑。")
        rsi_overbought = st.slider("RSI超买线", 60, 90, 70,
                                   help="当RSI超过此值时视为超买，可能回调。")
        rsi_oversold = st.slider("RSI超卖线", 10, 40, 30,
                                 help="当RSI低于此值时视为超卖，可能反弹。")

    st.subheader("⚙️ 策略回测参数")
    strategy = st.selectbox("策略类型", ["双均线", "RSI策略", "布林带策略"],
                            help="不同策略的适用场景不同：双均线适合趋势市，RSI适合震荡市，布林带适合波动率交易。")
    if strategy == "双均线":
        short_ma = st.slider("短期均线", 2, 50, 5,
                             help="金叉中的短期均线，通常设为5或10。")
        long_ma = st.slider("长期均线", 10, 200, 20,
                            help="金叉中的长期均线，通常设为20或60。短期均线上穿长期均线产生买入信号。")
        with st.container():
            st.caption("💡 **思考一下**")
            st.caption(f"短期均线 {short_ma} 天 vs 长期均线 {long_ma} 天，如果缩短短期均线，信号会更敏感；如果拉长长期均线，会过滤更多噪音。您觉得当前股票更适合哪种？")
    elif strategy == "RSI策略":
        rsi_period_strat = st.slider("RSI周期", 5, 30, 14,
                                     help="策略使用的RSI计算周期。")
        rsi_oversold_strat = st.slider("买入阈值(RSI<)", 10, 40, 30,
                                       help="当RSI低于此值时买入（超卖反弹）。")
        rsi_overbought_strat = st.slider("卖出阈值(RSI>)", 60, 90, 70,
                                         help="当RSI高于此值时卖出（超买回调）。")
        with st.container():
            st.caption("💡 **思考一下**")
            st.caption(f"RSI({rsi_period_strat}) 低于 {rsi_oversold_strat} 买入，高于 {rsi_overbought_strat} 卖出。如果市场处于强趋势，RSI可能长时间超买或超卖，需要结合趋势判断。")
    else:  # 布林带策略
        bb_period_strat = st.slider("布林带周期", 10, 50, 20,
                                    help="策略使用的布林带周期。")
        bb_std_strat = st.slider("标准差倍数", 1.0, 3.0, 2.0,
                                 help="策略使用的标准差倍数。")
        with st.container():
            st.caption("💡 **思考一下**")
            st.caption(f"布林带宽度 = {bb_std_strat}倍标准差，宽度越大，价格触及轨道的难度越大。您可以调整倍数以适应股票的波动特征。")
    commission = st.number_input("手续费率", value=0.001, format="%.4f",
                                 help="单边交易成本（例如0.001代表0.1%）。实盘交易必须考虑，否则回测会偏乐观。")
    slippage = st.number_input("滑点", value=0.001, format="%.4f",
                               help="因市场流动性导致的成交价差，通常设0.05%~0.1%。")

    # 多策略对比控件
    st.subheader("📈 多策略对比")
    enable_compare = st.checkbox("启用多策略对比", value=False,
                                 help="同时运行多个策略，对比资金曲线和绩效。")
    comp_short = 5
    comp_long = 20
    comp_rsi_period = 14
    comp_rsi_os = 30
    comp_rsi_ob = 70
    comp_bb_period = 20
    comp_bb_std = 2.0
    if enable_compare:
        compare_strategies = st.multiselect("选择策略", ["双均线", "RSI策略", "布林带策略"], default=["双均线", "RSI策略"])
        with st.expander("自定义对比参数"):
            if "双均线" in compare_strategies:
                comp_short = st.slider("对比-短期均线", 2, 50, 5, key="comp_short")
                comp_long = st.slider("对比-长期均线", 10, 200, 20, key="comp_long")
            if "RSI策略" in compare_strategies:
                comp_rsi_period = st.slider("对比-RSI周期", 5, 30, 14, key="comp_rsi_period")
                comp_rsi_os = st.slider("对比-买入阈值", 10, 40, 30, key="comp_rsi_os")
                comp_rsi_ob = st.slider("对比-卖出阈值", 60, 90, 70, key="comp_rsi_ob")
            if "布林带策略" in compare_strategies:
                comp_bb_period = st.slider("对比-布林带周期", 10, 50, 20, key="comp_bb_period")
                comp_bb_std = st.slider("对比-标准差倍数", 1.0, 3.0, 2.0, key="comp_bb_std")
    else:
        compare_strategies = []

    # 热力图控件
    st.subheader("🔥 双均线热力图")
    enable_heatmap = st.checkbox("启用热力图", value=False,
                                 help="网格搜索双均线参数组合的夏普比率，直观找到最优参数。")
    if enable_heatmap:
        hm_short = st.slider("短期范围", 2, 30, (3,15), key="hm_short")
        hm_long = st.slider("长期范围", 10, 100, (20,60), key="hm_long")
        hm_step = st.slider("步长", 1, 5, 2, key="hm_step")
        run_heatmap = st.button("生成热力图")
    else:
        run_heatmap = False

    # 指标百科折叠面板
    with st.expander("📚 指标百科（点击展开）", expanded=False):
        indicator_glossary()

    analyze = st.button("🚀 开始分析", type="primary", use_container_width=True)

# ================== 主区域 ==================
st.title("📊 MiniQuant 量化分析平台")
st.markdown("### 让散户像量化研究员一样分析股票")

if analyze:
    with st.spinner("正在加载数据..."):
        df = get_stock_data(symbol, start_date.strftime('%Y%m%d'), end_date.strftime('%Y%m%d'))
        if df.empty:
            st.error("未获取到数据，请检查股票代码或日期范围")
            st.stop()
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
        fig_main = plot_candlestick_with_indicators(df, ma_periods, bb_period, bb_std, show_candlestick)
        st.plotly_chart(fig_main, use_container_width=True)

        # 副图
        if show_rsi:
            st.caption("RSI 指标解释：衡量近期涨跌强度，低于30超卖（可能反弹），高于70超买（可能回调）。")
            fig_rsi = plot_rsi(df, rsi_period, rsi_overbought, rsi_oversold)
            st.plotly_chart(fig_rsi, use_container_width=True)
        if show_macd:
            st.caption("MACD 指标解释：快慢线金叉为买入信号，死叉为卖出信号；柱状线由负转正表示多头增强。")
            fig_macd = plot_macd(df)
            st.plotly_chart(fig_macd, use_container_width=True)
        if show_kdj:
            st.caption("KDJ 指标解释：K、D线低于20超卖，高于80超买；金叉买入，死叉卖出。")
            fig_kdj = plot_kdj(df)
            st.plotly_chart(fig_kdj, use_container_width=True)

        # 单策略回测
        st.subheader("策略回测")
        if strategy == "双均线":
            df_strat = ma_strategy(df, short_ma, long_ma)
            params = {'short_ma': short_ma, 'long_ma': long_ma}
        elif strategy == "RSI策略":
            df_strat = rsi_strategy(df, rsi_period_strat, rsi_oversold_strat, rsi_overbought_strat)
            params = {'period': rsi_period_strat, 'oversold': rsi_oversold_strat, 'overbought': rsi_overbought_strat}
        else:
            df_strat = bollinger_strategy(df, bb_period_strat, bb_std_strat)
            params = {'period': bb_period_strat, 'std_dev': bb_std_strat}
        df_strat = run_backtest(df_strat, commission, slippage)
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
        if enable_compare and len(compare_strategies) > 0:
            st.subheader("📊 多策略资金曲线对比")
            configs = []
            if "双均线" in compare_strategies:
                configs.append({'name':'双均线', 'strategy_func':ma_strategy, 'params':{'short_ma':comp_short, 'long_ma':comp_long}})
            if "RSI策略" in compare_strategies:
                configs.append({'name':'RSI策略', 'strategy_func':rsi_strategy, 'params':{'period':comp_rsi_period, 'oversold':comp_rsi_os, 'overbought':comp_rsi_ob}})
            if "布林带策略" in compare_strategies:
                configs.append({'name':'布林带策略', 'strategy_func':bollinger_strategy, 'params':{'period':comp_bb_period, 'std_dev':comp_bb_std}})
            results = multi_strategy_backtest(df, configs, commission, slippage)
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
        if enable_heatmap and run_heatmap:
            st.subheader("🔥 双均线夏普热力图")
            with st.spinner("网格搜索中，请稍候..."):
                short_vals, long_vals, sharpe_mat = grid_search_ma(df, hm_short, hm_long, step=hm_step, commission=commission, slippage=slippage)
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
else:
    st.info("请在左侧设置参数后点击「开始分析」")