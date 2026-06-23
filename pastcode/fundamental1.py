# fundamental.py (替换原文件)
import os
import json
import pandas as pd
import tushare as ts
from datetime import datetime, timedelta

CACHE_DIR = "fundamental_cache"
TUSHARE_TOKEN = os.environ.get("TUSHARE_TOKEN")
if not TUSHARE_TOKEN:
    print("警告: 未设置 TUSHARE_TOKEN，基本面数据将无法获取")
else:
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()

def ensure_cache_dir():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

def get_cache_file(symbol, date_str):
    return os.path.join(CACHE_DIR, f"{symbol}_{date_str}.json")

def is_cache_valid(symbol, date_str):
    cache_file = get_cache_file(symbol, date_str)
    if not os.path.exists(cache_file):
        return False
    mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
    return datetime.now() - mtime < timedelta(hours=24)

def save_cache(symbol, date_str, data):
    cache_file = get_cache_file(symbol, date_str)
    with open(cache_file, 'w') as f:
        json.dump(data, f)

def load_cache(symbol, date_str):
    cache_file = get_cache_file(symbol, date_str)
    try:
        with open(cache_file, 'r') as f:
            return json.load(f)
    except:
        return None

def get_fundamental(symbol, query_date):
    """
    获取指定日期之前最近一个交易日的 PE、PB、总市值（万元）
    query_date: datetime 对象或 'YYYYMMDD' 字符串
    """
    if TUSHARE_TOKEN is None:
        return None
    ensure_cache_dir()
    date_str = pd.to_datetime(query_date).strftime('%Y%m%d')
    cache_file = get_cache_file(symbol, date_str)
    if is_cache_valid(symbol, date_str):
        return load_cache(symbol, date_str)

    ts_code = f"{symbol}.SH" if symbol.startswith('6') else f"{symbol}.SZ"
    # 向前查找最多10个交易日，找到最近一个有数据的日期
    found_date = None
    for offset in range(10):
        test_date = (pd.to_datetime(query_date) - timedelta(days=offset)).strftime('%Y%m%d')
        df_test = pro.daily_basic(ts_code=ts_code, trade_date=test_date, fields='ts_code')
        if not df_test.empty:
            found_date = test_date
            break
    if not found_date:
        return None
    # 获取该日期的估值数据
    df = pro.daily_basic(ts_code=ts_code, trade_date=found_date, fields='pe_ttm,pb,total_mv')
    if df.empty:
        return None
    pe = df.iloc[0]['pe_ttm']
    pb = df.iloc[0]['pb']
    total_mv = df.iloc[0]['total_mv']  # 万元
    result = {
        'PE': round(pe, 2) if pd.notna(pe) else None,
        'PB': round(pb, 2) if pd.notna(pb) else None,
        '市值(亿)': round(total_mv / 10000, 2) if pd.notna(total_mv) else None,
        'ROE': None  # 本模块不提供ROE，若需要可用利润表接口单独获取
    }
    save_cache(symbol, date_str, result)
    return result