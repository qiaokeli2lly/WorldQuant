# strategies/bollinger_strategy.py
import pandas as pd

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