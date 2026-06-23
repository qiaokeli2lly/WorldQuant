# data/index_data.py
""" 获取沪深300等指数日线数据，带缓存 """
import pandas as pd
import os
from datetime import datetime, timedelta
import tushare as ts

INDEX_CACHE_DIR = "index_cache"

def ensure_cache_dir():
    if not os.path.exists(INDEX_CACHE_DIR):
        os.makedirs(INDEX_CACHE_DIR)

def get_index_data(code='000300.SH', start_date='', end_date=''):
    """返回 DataFrame，包含 date, close, return 等字段"""
    ensure_cache_dir()
    cache_file = os.path.join(INDEX_CACHE_DIR, f"{code.replace('.','_')}.csv")
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)

    # 尝试从缓存加载
    if os.path.exists(cache_file):
        cached = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        if not cached.empty and cached.index.min() <= start and cached.index.max() >= end:
            return cached.loc[start:end].copy()

    # 从 tushare 获取
    try:
        pro = ts.pro_api()
        df = pro.index_daily(ts_code=code, start_date=start.strftime('%Y%m%d'),
                              end_date=end.strftime('%Y%m%d'))
        if df.empty:
            return pd.DataFrame()
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df.set_index('trade_date', inplace=True)
        df.sort_index(inplace=True)
        df['return'] = df['close'].pct_change()
        # 更新缓存（合并旧数据）
        if os.path.exists(cache_file):
            old = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            df = pd.concat([old, df]).drop_duplicates().sort_index()
        df.to_csv(cache_file)
        return df.loc[start:end].copy()
    except Exception:
        return pd.DataFrame()