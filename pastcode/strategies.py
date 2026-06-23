# strategies.py
import pandas as pd

def ma_strategy(df, short_ma, long_ma):
    """双均线策略：短期均线上穿长期均线买入，下穿卖出"""
    df = df.copy()
    ma_short = f'MA{short_ma}'
    ma_long = f'MA{long_ma}'
    if ma_short not in df.columns or ma_long not in df.columns:
        raise ValueError(f"缺少 {ma_short} 或 {ma_long} 列")
    df['position'] = (df[ma_short] > df[ma_long]).astype(int)
    df['signal'] = df['position'].diff()
    return df

def rsi_strategy(df, period, oversold, overbought):
    """RSI策略：RSI低于超卖线买入，高于超买线卖出"""
    df = df.copy()
    rsi_col = f'RSI_{period}'
    if rsi_col not in df.columns:
        raise ValueError(f"缺少 {rsi_col} 列")
    df['position'] = 0
    df.loc[df[rsi_col] < oversold, 'position'] = 1
    df.loc[df[rsi_col] > overbought, 'position'] = 0
    df['signal'] = df['position'].diff()
    return df

def bollinger_strategy(df, period, std_dev):
    """布林带策略：收盘价触及下轨买入，触及上轨卖出"""
    df = df.copy()
    if 'BB_lower' not in df.columns or 'BB_upper' not in df.columns:
        raise ValueError("缺少布林带列，请先计算布林带")
    df['position'] = 0
    df.loc[df['close'] <= df['BB_lower'], 'position'] = 1
    df.loc[df['close'] >= df['BB_upper'], 'position'] = 0
    df['signal'] = df['position'].diff()
    return df