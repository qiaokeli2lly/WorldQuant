import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import tushare as ts
from data_utils import get_stock_data
from indicators import compute_all_indicators
from backtest import run_backtest, calculate_metrics, multi_strategy_backtest, grid_search_ma
from strategies import ma_strategy, rsi_strategy, bollinger_strategy
from plot_charts import plot_equity_curve
from fundamental import get_fundamental

st.set_page_config(layout="wide", page_title="MiniQuant 量化分析平台", page_icon="📈")

# ================== 辅助绘图函数（与之前相同，省略重复代码，可复制原版） ==================
def plot_candlestick_with_indicators(df, ma_periods, bb_period, bb_std, show_candlestick):
    # 此函数保持原样，篇幅原因省略，请从之前的版本复制
    pass

def plot_rsi(df, period, overbought, oversold):
    pass

def plot_macd(df):
    pass

def plot_kdj(df):
    pass

# 由于篇幅，这里只给出核心逻辑，实际使用时请将原有绘图函数完整复制过来。

# ================== 侧边栏 ==================
with st.sidebar:
    st.header("🔧 参数设置")
    
    # 热门股票快速选择（与原版相同）
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
        st.session_state['symbol'] = "600519"
    symbol = st.text_input("📈 股票代码", value=st.session_state['symbol'], help="6位数字A股代码").upper()
    st.session_state['symbol'] = symbol

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("📅 开始日期", value=pd.to_datetime("2022-01-01"))
    with col2:
        end_date = st.date_input("📅 结束日期", value=pd.to_datetime("2024-12-31"))

    st.subheader("📊 技术指标参数")
    ma_periods = st.multiselect("移动平均线周期", options=[5,10,20,30,60,120,250], default=[5,20,60])
    bb_period = st.slider("布林带周期", 10, 50, 20)
    bb_std = st.slider("布林带标准差倍数", 1.0, 3.0, 2.0, step=0.1)
    show_candlestick = st.radio("主图样式", ["K线", "收盘线"], index=0) == "K线"

    st.subheader("📉 副图指标")
    show_rsi = st.checkbox("RSI", value=True)
    show_macd = st.checkbox("MACD", value=False)
    show_kdj = st.checkbox("KDJ", value=False)
    if show_rsi:
        rsi_period = st.slider("RSI周期", 5, 30, 14)
        rsi_overbought = st.slider("RSI超买线", 60, 90, 70)
        rsi_oversold = st.slider("RSI超卖线", 10, 40, 30)

    st.subheader("⚙️ 策略回测参数")
    strategy = st.selectbox("策略类型", ["双均线", "RSI策略", "布林带策略"])
    if strategy == "双均线":
        short_ma = st.slider("短期均线", 2, 50, 5)
        long_ma = st.slider("长期均线", 10, 200, 20)
    elif strategy == "RSI策略":
        rsi_period_strat = st.slider("RSI周期", 5, 30, 14)
        rsi_oversold_strat = st.slider("买入阈值(RSI<)", 10, 40, 30)
        rsi_overbought_strat = st.slider("卖出阈值(RSI>)", 60, 90, 70)
    else:
        bb_period_strat = st.slider("布林带周期", 10, 50, 20)
        bb_std_strat = st.slider("标准差倍数", 1.0, 3.0, 2.0)

    # 新增：策略优化选项
    st.subheader("🛡️ 策略优化选项")
    enable_trend_filter = st.checkbox("启用大盘趋势过滤", value=False,
                                      help="仅当沪深300指数在20日均线之上时才允许买入")
    enable_dynamic_stop = st.checkbox("启用动态止损 (基于ATR)", value=False,
                                      help="当价格下跌超过2倍ATR时强制平仓")
    stop_loss_atr_mult = st.slider("ATR止损倍数", 1.0, 5.0, 2.0, step=0.5,
                                   help="止损价 = 买入价 - ATR × 倍数", disabled=not enable_dynamic_stop)
    enable_volume_filter = st.checkbox("启用成交量确认", value=False,
                                       help="信号出现时，成交量需大于过去20日均量的1.5倍")

    commission = st.number_input("手续费率", value=0.001, format="%.4f")
    slippage = st.number_input("滑点", value=0.001, format="%.4f")

    # 多策略对比和热力图控件（与原版相同，省略）
    # ...（此处保留原有多策略对比和热力图代码）

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

        # 基本面数据面板
        with st.expander("📊 基本面数据（最新一期）", expanded=False):
            with st.spinner("加载中..."):
                fund = get_fundamental(symbol)
                if fund:
                    f_col1, f_col2, f_col3 = st.columns(3)
                    f_col1.metric("市盈率(PE)", fund.get('PE', '-'))
                    f_col2.metric("市净率(PB)", fund.get('PB', '-'))
                    f_col3.metric("市值(亿元)", fund.get('市值(亿)', '-'))
                    st.caption(f"营收: {fund.get('营收(亿)', '-')}亿  净利润: {fund.get('净利润(亿)', '-')}亿  ROE: {fund.get('ROE(%)', '-')}%")
                    if fund.get('资产负债率'):
                        st.caption(f"资产负债率: {fund['资产负债率']:.2%}  营收同比增长率: {fund.get('营收同比增长率', '-')}")
                else:
                    st.info("暂无基本面数据，请检查 Tushare token 或网络")

        # 主图（此处调用绘图函数，需补充完整）
        st.subheader("价格走势与技术指标")
        # fig_main = plot_candlestick_with_indicators(df, ...)  # 请补充完整
        # st.plotly_chart(fig_main)

        # 副图（同上）
        # ...

        # 策略回测（核心）
        st.subheader("策略回测")
        if strategy == "双均线":
            df_strat = ma_strategy(df, short_ma, long_ma)
        elif strategy == "RSI策略":
            df_strat = rsi_strategy(df, rsi_period_strat, rsi_oversold_strat, rsi_overbought_strat)
        else:
            df_strat = bollinger_strategy(df, bb_period_strat, bb_std_strat)

        # 大盘趋势过滤
        if enable_trend_filter:
            try:
                pro = ts.pro_api()
                idx_df = pro.index_daily(ts_code='000300.SH', start_date=start_date.strftime('%Y%m%d'), end_date=end_date.strftime('%Y%m%d'))
                idx_df['trade_date'] = pd.to_datetime(idx_df['trade_date'])
                idx_df.set_index('trade_date', inplace=True)
                idx_df['MA20'] = idx_df['close'].rolling(20).mean()
                idx_signal = (idx_df['close'] > idx_df['MA20']).reindex(df.index, method='ffill').fillna(True)
                df_strat['position'] = df_strat['position'] * idx_signal.astype(int)
                df_strat['signal'] = df_strat['position'].diff()
            except Exception as e:
                st.warning(f"获取指数数据失败，趋势过滤已禁用: {e}")

        # 成交量确认
        if enable_volume_filter:
            df_strat['volume_ma20'] = df['volume'].rolling(20).mean()
            volume_ok = df['volume'] > df['volume_ma20'] * 1.5
            buy_signals = (df_strat['signal'] == 1) & ~volume_ok
            df_strat.loc[buy_signals, 'signal'] = 0
            df_strat['position'] = df_strat['position'].where(~buy_signals, 0)

        # 运行回测（传入动态止损参数）
        df_strat = run_backtest(df_strat, commission=commission, slippage=slippage,
                                stop_loss_atr_mult=stop_loss_atr_mult if enable_dynamic_stop else None)

        metrics = calculate_metrics(df_strat)
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("年化收益率", f"{metrics.get('年化收益率（策略）',0)*100:.2f}%")
        col_b.metric("夏普比率", f"{metrics.get('夏普比率',0):.2f}")
        col_c.metric("最大回撤", f"{metrics.get('最大回撤',0)*100:.2f}%")

        # 资金曲线图
        fig_curve = plot_equity_curve(df_strat, benchmark_col='benchmark_net', strategy_col='strategy_net')
        st.pyplot(fig_curve)

        # 单日数据查看器、最近20日数据表格等（省略，可保留原有代码）

        st.success("分析完成！")
else:
    st.info("请在左侧设置参数后点击「开始分析」")