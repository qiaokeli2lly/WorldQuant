# factor_preprocess.py
import pandas as pd
import numpy as np

def winsorize(series, limit=0.01):
    if series.nunique() <= 2:
        return series
    lower = series.quantile(limit)
    upper = series.quantile(1-limit)
    return series.clip(lower, upper)

def standardize(series):
    if series.std() == 0:
        return series - series.mean()
    return (series - series.mean()) / series.std()

def preprocess_factors(factor_df, factor_cols):
    df = factor_df.copy()
    for col in factor_cols:
        if col in df.columns and df[col].notna().any():
            # 先 winsorize 再标准化
            df[col] = winsorize(df[col])
            df[col] = standardize(df[col])
        else:
            # 如果该列不存在或全为 NaN，统一设为 NaN（后续由外部 fillna(0) 处理）
            df[col] = np.nan
    return df