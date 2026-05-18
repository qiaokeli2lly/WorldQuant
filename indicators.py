import pandas as pd
import numpy as np

def add_moving_averages(df, windows=[5, 20, 60]):
    """
    添加简单移动平均线 (SMA)
    :param df: 包含 'close' 列的 DataFrame
    :param windows: 周期列表，例如 [5, 20, 60]
    """
    for w in windows:
        df[f'MA{w}'] = df['close'].rolling(window=w).mean()
    return df

def add_exponential_moving_average(df, span=12):
    """
    添加指数移动平均线 (EMA)
    :param span: 周期，例如 12
    """
    df[f'EMA{span}'] = df['close'].ewm(span=span, adjust=False).mean()
    return df

def add_rsi(df, period=14):
    """
    添加相对强弱指数 (RSI)
    :param period: 计算周期，默认14
    """
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    # 使用简单移动平均计算平均涨幅/跌幅
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    # 避免除以零
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    df[f'RSI_{period}'] = rsi
    return df

def add_bollinger_bands(df, period=20, std_dev=2):
    """
    添加布林带 (Bollinger Bands)
    :param period: 中轨周期，默认20
    :param std_dev: 标准差倍数，默认2
    """
    mid = df['close'].rolling(window=period).mean()
    std = df['close'].rolling(window=period).std()
    df['BB_mid'] = mid
    df['BB_upper'] = mid + std_dev * std
    df['BB_lower'] = mid - std_dev * std
    return df

def add_volume_ratio(df, period=20):
    """
    添加成交量比率（当前成交量 / 过去period天平均成交量）
    :param period: 平均周期，默认20
    """
    df['volume_ma'] = df['volume'].rolling(window=period).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma']
    return df

def compute_all_indicators(df):
    """
    一次性计算所有常用指标
    """
    df = add_moving_averages(df, windows=[5, 20, 60])
    df = add_exponential_moving_average(df, span=12)
    df = add_rsi(df, period=14)
    df = add_bollinger_bands(df, period=20, std_dev=2)
    df = add_volume_ratio(df, period=20)
    return df

if __name__ == "__main__":
    # 测试：从缓存读取数据并计算指标
    from data_utils import get_stock_data
    df = get_stock_data("000568", "20250201", "20250228")
    df = compute_all_indicators(df)
    print(df[['close', 'MA5', 'MA20', 'RSI_14', 'BB_upper', 'BB_lower', 'volume_ratio']].tail(10))