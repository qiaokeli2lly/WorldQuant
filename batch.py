# factors/batch.py
""" 批量因子计算（独立接口，可直接调用） """
import pandas as pd
import numpy as np
from data.stock_data import get_stock_data
from data.fundamental import get_fundamental_batch   # 保留作为 fallback，但通常不需
from factors.price_factors import (
    calc_momentum, calc_reversal, calc_volatility,
    calc_rpv, calc_new_momentum, calc_combo_vol_price
)
from factors.fundamental_factors import transform_pe, transform_pb, safe_float


def get_all_factors_batch(symbols, date, data_dict=None, value_dict=None,
                          lookbacks=None, use_fundamental=False):
    """
    批量获取多只股票在指定日期的因子值。

    参数:
        symbols: 股票代码列表
        date: pandas Timestamp 或日期字符串
        data_dict: {symbol: DataFrame} 预加载的行情数据（可选，若提供则直接切片）
        value_dict: {symbol: DataFrame} 预加载的估值数据（可选，用于快速获取PE/PB）
        lookbacks: dict，各因子的回溯天数，默认 {'momentum':20, 'reversal':5, 'volatility':20}
        use_fundamental: 是否计算PE/PB因子

    返回:
        dict: {symbol: {factor_name: value}}
    """
    if lookbacks is None:
        lookbacks = {'momentum': 20, 'reversal': 5, 'volatility': 20}

    result = {}
    max_lookback = max(lookbacks.values()) + 60   # 额外缓冲天数

    for sym in symbols:
        # ---------- 获取行情数据 ----------
        if data_dict and sym in data_dict:
            df_full = data_dict[sym]
            df = df_full.loc[:date]
            if len(df) < max_lookback:
                continue
            df = df.iloc[-max_lookback:]
        else:
            hist_start = (pd.to_datetime(date) - pd.Timedelta(days=max_lookback)).strftime('%Y%m%d')
            hist_end = pd.to_datetime(date).strftime('%Y%m%d')
            df = get_stock_data(sym, hist_start, hist_end)
            if df.empty or len(df) < lookbacks['momentum']:
                continue

        close = df['close']
        volume = df['volume'] if 'volume' in df.columns else None

        # 计算量价因子
        mom = calc_momentum(close, lookbacks['momentum'])
        rev = calc_reversal(close, lookbacks['reversal'])
        vol = calc_volatility(close, lookbacks['volatility'])
        if any(pd.isna(x) for x in [mom, rev, vol]):
            continue

        rpv = calc_rpv(close, volume, 20) if volume is not None else np.nan
        new_mom = calc_new_momentum(close)
        combo = calc_combo_vol_price(close)

        # ---------- 基本面因子 ----------
        pe_score = np.nan
        pb_score = np.nan
        if use_fundamental:
            if value_dict and sym in value_dict:
                # 从估值字典中取对应日期的PE/PB
                val_df = value_dict[sym]
                target_date = pd.to_datetime(date)
                if target_date in val_df.index:
                    row = val_df.loc[target_date]
                    pe_raw = row.get('PE', np.nan)
                    pb_raw = row.get('PB', np.nan)
                    pe_score = transform_pe(pe_raw) if not pd.isna(pe_raw) else np.nan
                    pb_score = transform_pb(pb_raw) if not pd.isna(pb_raw) else np.nan
            else:
                # 回退到实时请求（不推荐，但保留兼容）
                fund = get_fundamental_batch([sym], pd.to_datetime(date).strftime('%Y%m%d'))
                pe_raw = safe_float(fund.get(sym, {}).get('PE'))
                pb_raw = safe_float(fund.get(sym, {}).get('PB'))
                pe_score = transform_pe(pe_raw) if not pd.isna(pe_raw) else np.nan
                pb_score = transform_pb(pb_raw) if not pd.isna(pb_raw) else np.nan

        result[sym] = {
            'momentum': mom,
            'reversal': rev,
            'volatility': vol,
            'rpv': rpv,
            'new_momentum': new_mom,
            'combo': combo,
            'pe': pe_score,
            'pb': pb_score,
        }
    return result