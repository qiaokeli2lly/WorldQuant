# strategies/ma_strategy.py
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