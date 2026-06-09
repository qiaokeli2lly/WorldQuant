import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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