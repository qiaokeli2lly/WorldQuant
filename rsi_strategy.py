# strategies/rsi_strategy.py
import pandas as pd

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