import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data_utils import get_stock_data
from indicators import compute_all_indicators
from backtest import generate_signals, run_backtest, calculate_metrics
from plot_charts import plot_equity_curve

st.set_page_config(layout="wide", page_title="MiniQuant 量化分析平台", page_icon="📈")

# ================== 绘图函数（修复悬停错误）==================
def plot_candlestick_with_indicators(df, ma_periods, bb_period, bb_std, show_candlestick):
    df = df.copy()
    # 标记真实交易日
    df['is_trading_day'] = (df['volume'] > 0) & (df['return'].notna())
    plot_df = df.copy()
    if show_candlestick:
        for col in ['open', 'high', 'low', 'close']:
            plot_df.loc[~plot_df['is_trading_day'], col] = np.nan

    fig = make_subplots(rows=1, cols=1)
    
    if show_candlestick:
        # customdata 包含: open, high, low, close, volume, 提示文本
        hint_text = ['⚠️ 非交易日（数据为前值填充）<br>' if not td else '' for td in plot_df['is_trading_day']]
        customdata = np.column_stack((
            plot_df['open'].values, plot_df['high'].values, plot_df['low'].values,
            plot_df['close'].values, plot_df['volume'].values, hint_text
        ))
        fig.add_trace(go.Candlestick(
            x=plot_df.index,
            open=plot_df['open'], high=plot_df['high'],
            low=plot_df['low'], close=plot_df['close'],
            name='K线',
            hovertemplate='<b>%{x}</b><br>%{customdata[5]}'
                          '开盘: %{customdata[0]:.2f}<br>'
                          '最高: %{customdata[1]:.2f}<br>'
                          '最低: %{customdata[2]:.2f}<br>'
                          '收盘: %{customdata[3]:.2f}<br>'
                          '成交量: %{customdata[4]:.0f} 手<extra></extra>',
            customdata=customdata
        ))
    else:
        hint_text = ['⚠️ 非交易日（数据为前值填充）<br>' if not td else '' for td in df['is_trading_day']]
        customdata = np.column_stack((df['volume'].values, hint_text))
        fig.add_trace(go.Scatter(
            x=df.index, y=df['close'], mode='lines', name='收盘价',
            line=dict(color='black', width=1.5),
            hovertemplate='<b>%{x}</b><br>%{customdata[1]}'
                          '收盘价: %{y:.2f}<br>'
                          '成交量: %{customdata[0]:.0f} 手<extra></extra>',
            customdata=customdata
        ))
    
    # 均线
    colors = ['blue', 'orange', 'red', 'green', 'purple']
    for i, p in enumerate(ma_periods):
        col = f'MA{p}'
        if col in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col], mode='lines', name=col,
                line=dict(color=colors[i % len(colors)], width=1),
                hovertemplate=f'<b>{col}</b>: %{{y:.2f}}<extra></extra>'
            ))
    # 布林带
    if 'BB_upper' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_upper'], mode='lines', name='BB上轨',
                                 line=dict(color='gray', dash='dash'),
                                 hovertemplate='<b>BB上轨</b>: %{y:.2f}<extra></extra>'))
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_lower'], mode='lines', name='BB下轨',
                                 line=dict(color='gray', dash='dash'),
                                 hovertemplate='<b>BB下轨</b>: %{y:.2f}<extra></extra>'))
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_mid'], mode='lines', name='BB中轨',
                                 line=dict(color='gray', width=1),
                                 hovertemplate='<b>BB中轨</b>: %{y:.2f}<extra></extra>'))
    
    fig.update_layout(
        title='价格走势',
        xaxis_title='日期',
        yaxis_title='价格',
        height=500,
        hovermode='x unified',
        hoverlabel=dict(bgcolor="white", font_size=12),
        xaxis=dict(tickformat='%Y-%m-%d', tickangle=45, rangeslider_visible=False)
    )
    return fig

def plot_rsi(df, period, overbought, oversold):
    col = f'RSI_{period}'
    fig = go.Figure()
    if col in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[col], mode='lines', name='RSI',
            line=dict(color='purple', width=1.5),
            hovertemplate='<b>日期</b>: %{x}<br><b>RSI</b>: %{y:.2f}<extra></extra>'
        ))
        fig.add_hline(y=overbought, line_dash="dash", line_color="red", annotation_text=f"超买线({overbought})", annotation_position="top right")
        fig.add_hline(y=oversold, line_dash="dash", line_color="green", annotation_text=f"超卖线({oversold})", annotation_position="bottom right")
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

# ================== 侧边栏 ==================
with st.sidebar:
    st.header("🔧 参数设置")
    symbol = st.text_input("📈 股票代码", value="600519", help="请输入6位数字的A股代码（例如：600519）").upper()
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("📅 开始日期", value=pd.to_datetime("2022-01-01"), help="回测起始日期，建议至少1年")
    with col2:
        end_date = st.date_input("📅 结束日期", value=pd.to_datetime("2024-12-31"), help="回测结束日期")
    
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
        bb_std_strat = st.slider("布林带标准差倍数", 1.0, 3.0, 2.0)
    commission = st.number_input("手续费率", value=0.001, format="%.4f")
    slippage = st.number_input("滑点", value=0.001, format="%.4f")
    
    with st.expander("📖 参数说明与技巧", expanded=False):
        st.markdown("""
        **为什么要调整参数？**  
        每个股票都有自己的“脾气”，通过调整参数可以找到更适合该股票的交易规则。

        ---
        **📈 移动平均线 (MA)**
        - **MA5**：5日均线，反映近一周的平均成本，适合短线参考。
        - **MA20**：20日均线（月线），常作为中期趋势的分水岭。
        - **MA60**：60日均线（季线），用于判断长期趋势方向。
        - **技巧**：短期均线上穿长期均线（金叉）视为买入信号，下穿（死叉）视为卖出信号。

        **📉 RSI（相对强弱指数）**
        - **取值0-100**：RSI < 30 为超卖区（可能反弹），RSI > 70 为超买区（可能回调）。
        - **周期选择**：周期越短（如7日）信号越敏感，但假信号也多；周期越长（如21日）信号更平滑。
        - **技巧**：RSI在震荡市中更有效，单边市中可能持续处于超买/超卖区域。

        **📊 布林带**
        - **中轨**：20日均线，代表股价的平衡位置。
        - **上下轨**：中轨 ± 2倍标准差，股价在上下轨之间波动为正常，突破轨道可能预示趋势加速。
        - **技巧**：股价触及下轨时可能超卖反弹，触及上轨时可能超买回落。

        **⚙️ 回测设置**
        - **手续费率**：建议设置0.1%-0.3%，真实反映交易成本。
        - **滑点**：因市场流动性导致的成交价差，建议设置0.05%-0.1%。
        - **注意**：回测结果越接近真实交易环境，参考价值越高。

        **💡 如何选择策略？**
        - **双均线**：趋势跟踪策略，适合有明显上涨或下跌趋势的行情。
        - **RSI策略**：均值回归策略，适合震荡行情（股价在区间内来回波动）。
        - **布林带策略**：波动率交易，适合在价格触及轨道时博取反弹或回落。

        **🔍 查看数据技巧**
        - 鼠标悬停在图表上可以查看具体日期的数值。
        - 使用鼠标框选可以放大任意时间段的细节。
        - 点击图例可以隐藏/显示对应的曲线。
        """)
    
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
        
        # 标记交易日（用于单日查看器）
        df['is_trading_day'] = (df['volume'] > 0) & (df['return'].notna())
        
        # 基本信息
        latest = df.iloc[-1]
        col1, col2, col3 = st.columns(3)
        col1.metric("最新价", f"{latest['close']:.2f}")
        col2.metric("涨跌幅", f"{(latest['close']/df.iloc[-2]['close']-1)*100:.2f}%")
        col3.metric("成交量(手)", f"{latest['volume']:.0f}")
        
        # 主图
        st.subheader("价格走势与技术指标")
        fig_main = plot_candlestick_with_indicators(df, ma_periods, bb_period, bb_std, show_candlestick)
        st.plotly_chart(fig_main, use_container_width=True)
        
        # 副图
        if show_rsi:
            fig_rsi = plot_rsi(df, rsi_period, rsi_overbought, rsi_oversold)
            st.plotly_chart(fig_rsi, use_container_width=True)
        if show_macd:
            fig_macd = plot_macd(df)
            st.plotly_chart(fig_macd, use_container_width=True)
        if show_kdj:
            fig_kdj = plot_kdj(df)
            st.plotly_chart(fig_kdj, use_container_width=True)
        
        # 策略回测
        st.subheader("策略回测")
        if strategy == "双均线":
            df_strat = generate_signals(df, short_ma, long_ma)
            df_strat = run_backtest(df_strat, commission=commission, slippage=slippage)
            metrics = calculate_metrics(df_strat)
        elif strategy == "RSI策略":
            df_strat = df.copy()
            rsi_col = f'RSI_{rsi_period_strat}'
            df_strat['position'] = 0
            df_strat.loc[df_strat[rsi_col] < rsi_oversold_strat, 'position'] = 1
            df_strat.loc[df_strat[rsi_col] > rsi_overbought_strat, 'position'] = 0
            df_strat['signal'] = df_strat['position'].diff()
            df_strat = run_backtest(df_strat, commission=commission, slippage=slippage)
            metrics = calculate_metrics(df_strat)
        else:
            st.info("布林带策略开发中...")
            st.stop()
        
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("年化收益率", f"{metrics.get('年化收益率（策略）',0)*100:.2f}%")
        col_b.metric("夏普比率", f"{metrics.get('夏普比率',0):.2f}")
        col_c.metric("最大回撤", f"{metrics.get('最大回撤',0)*100:.2f}%")
        
        # 资金曲线
        fig_curve = plot_equity_curve(df_strat, benchmark_col='benchmark_net', strategy_col='strategy_net')
        st.pyplot(fig_curve)
        
        # 单日数据查看器
        st.subheader("📅 单日数据详情")
        col_date, col_btn = st.columns([3,1])
        with col_date:
            selected_date = st.date_input("选择日期", value=df.index[-1], min_value=df.index.min(), max_value=df.index.max())
        with col_btn:
            if st.button("查看详情"):
                if selected_date in df.index:
                    row = df.loc[selected_date]
                    is_trading = row['is_trading_day']
                    if not is_trading:
                        st.warning(f"⚠️ {selected_date} 为非交易日，数据为前一日填充值，仅供参考。")
                    st.write(f"**开盘**: {row['open']:.2f}  **最高**: {row['high']:.2f}  **最低**: {row['low']:.2f}  **收盘**: {row['close']:.2f}")
                    st.write(f"**成交量**: {row['volume']:.0f} 手  **涨跌幅**: {row['return']*100:.2f}%" if pd.notna(row['return']) else "**涨跌幅**: -")
                else:
                    st.error("所选日期不在数据范围内")
        
        # 最近20日数据表格
        with st.expander("📋 查看最近20日原始数据"):
            st.dataframe(df[['open','high','low','close','volume','return','is_trading_day']].tail(20).style.format({
                'open': '{:.2f}', 'high': '{:.2f}', 'low': '{:.2f}', 'close': '{:.2f}',
                'volume': '{:.0f}', 'return': '{:.4%}'
            }))
        
        st.success("分析完成！")
else:
    st.info("请在左侧设置参数后点击「开始分析」")