# factors/price_factors.py
""" 纯量价因子计算函数，不依赖外部数据源 """
import numpy as np
import pandas as pd

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