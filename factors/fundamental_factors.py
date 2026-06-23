# factors/fundamental_factors.py
""" 基本面因子转换函数，确保低估值对应高得分 """
import numpy as np

def safe_float(val):
    try:
        return float(val)
    except:
        return np.nan

def transform_pe(pe_raw):
    if np.isnan(pe_raw):
        return np.nan
    return -pe_raw      # 越低越好，所以取负数

def transform_pb(pb_raw):
    if np.isnan(pb_raw):
        return np.nan
    return -pb_raw