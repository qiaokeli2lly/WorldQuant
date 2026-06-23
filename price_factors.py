# factors/price_factors.py
import numpy as np
import pandas as pd

# ---------- 动量 ----------
def calc_momentum(close_series, lookback=20):
    if len(close_series) < lookback:
        return np.nan
    return close_series.iloc[-1] / close_series.iloc[-lookback] - 1

def calc_reversal(close_series, lookback=5):
    if len(close_series) < lookback:
        return np.nan
    ret = close_series.iloc[-1] / close_series.iloc[-lookback] - 1
    return -ret

def calc_volatility(close_series, lookback=20):
    if len(close_series) < lookback:
        return np.nan
    daily_ret = close_series.pct_change().dropna()
    if len(daily_ret) < lookback:
        return np.nan
    vol = daily_ret.iloc[-lookback:].std()
    return -vol

def calc_rpv(close_series, volume_series, lookback=20):
    if len(close_series) < lookback:
        return np.nan
    close = close_series.astype(float)
    volume = volume_series.astype(float)
    corr = close.rolling(lookback).corr(volume)
    return corr.iloc[-1]

def calc_new_momentum(close_series, lookback_far=60, lookback_near=5):
    if len(close_series) < lookback_far:
        return np.nan
    near_price = close_series.iloc[-lookback_near]
    far_price = close_series.iloc[-lookback_far]
    return near_price / far_price - 1

def calc_combo_vol_price(close_series):
    mom = calc_momentum(close_series, 20)
    rev = calc_reversal(close_series, 5)
    vol = calc_volatility(close_series, 20)
    if any(pd.isna(x) for x in [mom, rev, vol]):
        return np.nan
    return (mom + rev + vol) / 3

# ---------- 新增技术指标 ----------
def calc_rsi(close_series, period=14):
    """返回最新 RSI 值"""
    if len(close_series) < period + 1:
        return np.nan
    delta = close_series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def calc_macd(close_series, fast=12, slow=26, signal=9):
    """返回 (MACD, signal, histogram) 的最新值"""
    if len(close_series) < slow:
        return np.nan, np.nan, np.nan
    exp1 = close_series.ewm(span=fast, adjust=False).mean()
    exp2 = close_series.ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    hist = macd - signal_line
    return macd.iloc[-1], signal_line.iloc[-1], hist.iloc[-1]

def calc_kdj(high_series, low_series, close_series, n=9, k_period=3, d_period=3):
    """返回 (K, D, J) 的最新值"""
    if len(close_series) < n:
        return np.nan, np.nan, np.nan
    low_min = low_series.rolling(n).min()
    high_max = high_series.rolling(n).max()
    rsv = (close_series - low_min) / (high_max - low_min) * 100
    k = rsv.ewm(span=k_period, adjust=False).mean()
    d = k.ewm(span=d_period, adjust=False).mean()
    j = 3 * k - 2 * d
    return k.iloc[-1], d.iloc[-1], j.iloc[-1]

def calc_bollinger(close_series, period=20, std_dev=2):
    """返回 (upper, lower, middle) 的最新值"""
    if len(close_series) < period:
        return np.nan, np.nan, np.nan
    mid = close_series.rolling(period).mean()
    std = close_series.rolling(period).std()
    upper = mid + std_dev * std
    lower = mid - std_dev * std
    return upper.iloc[-1], lower.iloc[-1], mid.iloc[-1]

def calc_volume_ratio(volume_series, period=5):
    """返回当前成交量与过去 period 日均量的比值"""
    if len(volume_series) < period:
        return np.nan
    return volume_series.iloc[-1] / volume_series.rolling(period).mean().iloc[-1]

def calc_atr(high_series, low_series, close_series, period=14):
    """返回最新 ATR 值"""
    if len(close_series) < period + 1:
        return np.nan
    high_low = high_series - low_series
    high_close = (high_series - close_series.shift(1)).abs()
    low_close = (low_series - close_series.shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr.iloc[-1]