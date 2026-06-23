# factor_calc.py
import os
import json
import pandas as pd
import numpy as np
import tushare as ts
from data.stock_data import get_stock_data
from data.fundamental import get_fundamental_batch

# ================== 辅助函数 ==================
def safe_float(val):
    try:
        return float(val)
    except:
        return np.nan

# ================== 原有量价因子 ==================
def calc_momentum(df, lookback=20):
    if len(df) < lookback:
        return np.nan
    return df['close'].iloc[-1] / df['close'].iloc[-lookback] - 1

def calc_reversal(df, lookback=5):
    if len(df) < lookback:
        return np.nan
    ret = df['close'].iloc[-1] / df['close'].iloc[-lookback] - 1
    return -ret

def calc_volatility(df, lookback=20):
    if len(df) < lookback:
        return np.nan
    daily_ret = df['close'].pct_change().dropna()
    if len(daily_ret) < lookback:
        return np.nan
    vol = daily_ret.iloc[-lookback:].std()
    return -vol

# ================== 新增高胜率因子 ==================
def calc_rpv(df, lookback=20):
    """
    新价量相关性 (RPV) - 收盘价与成交量的滚动相关系数
    """
    if len(df) < lookback:
        return np.nan
    close = df['close'].astype(float)
    volume = df['volume'].astype(float)
    corr = close.rolling(lookback).corr(volume)
    return corr.iloc[-1]

def calc_new_momentum(df, lookback_far=60, lookback_near=5):
    """
    新动量因子：剔除最近5日，使用过去60日至5日的收益率
    """
    if len(df) < lookback_far:
        return np.nan
    near_price = df['close'].iloc[-lookback_near]
    far_price = df['close'].iloc[-lookback_far]
    return near_price / far_price - 1

def calc_combo_vol_price(df):
    """
    综合量价因子：等权合成动量、反转、波动率
    """
    mom = calc_momentum(df, 20)
    rev = calc_reversal(df, 5)
    vol = calc_volatility(df, 20)
    if any(pd.isna(x) for x in [mom, rev, vol]):
        return np.nan
    return (mom + rev + vol) / 3

# ================== 批量获取因子（整合所有） ==================
def get_all_factors_batch(symbols, date, lookbacks=None, min_mcap=50):
    """
    批量获取多只股票在指定日期的所有因子值
    包括：动量、反转、波动率、RPV、新动量、综合量价、PE、PB、市值
    """
    if lookbacks is None:
        lookbacks = {'momentum':20, 'reversal':5, 'volatility':20}
    trade_date_str = date.strftime('%Y%m%d')
    # 获取基本面估值数据（PE,PB,市值），失败时返回空字典不会中断
    fund_data = get_fundamental_batch(symbols, trade_date_str)
    result = {}

    for sym in symbols:
        # 获取量价数据
        hist_start = (date - pd.Timedelta(days=max(lookbacks.values())+60)).strftime('%Y%m%d')
        hist_end = date.strftime('%Y%m%d')
        df = get_stock_data(sym, hist_start, hist_end)
        if df.empty or len(df) < max(lookbacks.values()):
            continue

        # 计算量价因子（必须全部有效才保留该股票）
        mom = calc_momentum(df, lookbacks['momentum'])
        rev = calc_reversal(df, lookbacks['reversal'])
        vol = calc_volatility(df, lookbacks['volatility'])
        if any(pd.isna(x) for x in [mom, rev, vol]):
            continue

        # 新增因子允许为 NaN，单独计算并保留
        rpv = calc_rpv(df, 20)
        new_mom = calc_new_momentum(df, 60, 5)
        combo = calc_combo_vol_price(df)

        # 基本面因子（可选，缺失时设为 NaN，不跳过股票）
        pe = safe_float(fund_data.get(sym, {}).get('PE'))
        pb = safe_float(fund_data.get(sym, {}).get('PB'))
        # 方向修正：低 PE/PB 得分高，因此取负数（或倒数），此处使用 -PE, -PB
        pe_score = -pe if not np.isnan(pe) else np.nan
        pb_score = -pb if not np.isnan(pb) else np.nan

        result[sym] = {
            'momentum': mom,
            'reversal': rev,
            'volatility': vol,
            'rpv': rpv,
            'new_momentum': new_mom,
            'combo': combo,
            'pe': pe_score,   # 已转换方向
            'pb': pb_score    # 已转换方向
        }
    return result