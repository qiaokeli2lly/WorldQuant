# fundamental.py
import os
import json
import pandas as pd
import tushare as ts
from datetime import datetime, timedelta

CACHE_DIR = "fundamental_cache"
TUSHARE_TOKEN = os.environ.get("TUSHARE_TOKEN")
if TUSHARE_TOKEN:
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
else:
    pro = None
    print("警告: TUSHARE_TOKEN 未设置，基本面数据无法获取")

def ensure_cache_dir():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

def get_cache_file(symbol, date_str):
    return os.path.join(CACHE_DIR, f"{symbol}_{date_str}.json")

def load_cache(symbol, date_str):
    fname = get_cache_file(symbol, date_str)
    if os.path.exists(fname):
        try:
            with open(fname, 'r') as f:
                return json.load(f)
        except:
            pass
    return None

def save_cache(symbol, date_str, data):
    fname = get_cache_file(symbol, date_str)
    with open(fname, 'w') as f:
        json.dump(data, f)

def get_fundamental_batch(symbols, trade_date):
    """
    批量获取指定日期所有股票的 PE、PB、总市值（万元）
    symbols: 列表，如 ['600519', '000858']
    trade_date: 'YYYYMMDD' 字符串
    返回字典 { symbol: {'PE':..., 'PB':..., '市值(亿)':...} }
    """
    if pro is None:
        return {}
    ensure_cache_dir()
    # 先尝试从缓存读取
    result = {}
    missing = []
    for sym in symbols:
        cached = load_cache(sym, trade_date)
        if cached is not None:
            result[sym] = cached
        else:
            missing.append(sym)
    if not missing:
        return result

    # 转换代码格式
    ts_codes = []
    for sym in missing:
        if sym.startswith('6'):
            ts_codes.append(f"{sym}.SH")
        else:
            ts_codes.append(f"{sym}.SZ")
    ts_code_str = ','.join(ts_codes)
    try:
        df = pro.daily_basic(ts_code=ts_code_str, trade_date=trade_date, fields='ts_code,pe_ttm,pb,total_mv')
        if df.empty:
            # 可能是非交易日，尝试向前找最近交易日
            # 简化：返回空，调用方会处理
            return result
        for _, row in df.iterrows():
            ts_code = row['ts_code']
            sym = ts_code.split('.')[0]
            pe = row['pe_ttm']
            pb = row['pb']
            total_mv = row['total_mv']  # 万元
            data = {
                'PE': round(pe, 2) if pd.notna(pe) else None,
                'PB': round(pb, 2) if pd.notna(pb) else None,
                '市值(亿)': round(total_mv / 10000, 2) if pd.notna(total_mv) else None
            }
            result[sym] = data
            save_cache(sym, trade_date, data)
    except Exception as e:
        print(f"批量获取基本面失败: {e}")
    return result

def get_fundamental(symbol, query_date):
    """
    获取单只股票在指定日期之前最近交易日的估值数据
    query_date: datetime 对象或 'YYYYMMDD' 字符串
    """
    if pro is None:
        return None
    ensure_cache_dir()
    date_str = pd.to_datetime(query_date).strftime('%Y%m%d')
    # 尝试缓存
    cached = load_cache(symbol, date_str)
    if cached is not None:
        return cached
    # 单只获取（向后兼容）
    ts_code = f"{symbol}.SH" if symbol.startswith('6') else f"{symbol}.SZ"
    # 向前查找最多10个交易日
    found_date = None
    for offset in range(10):
        test_date = (pd.to_datetime(query_date) - timedelta(days=offset)).strftime('%Y%m%d')
        df_test = pro.daily_basic(ts_code=ts_code, trade_date=test_date, fields='ts_code')
        if not df_test.empty:
            found_date = test_date
            break
    if not found_date:
        return None
    df = pro.daily_basic(ts_code=ts_code, trade_date=found_date, fields='pe_ttm,pb,total_mv')
    if df.empty:
        return None
    pe = df.iloc[0]['pe_ttm']
    pb = df.iloc[0]['pb']
    total_mv = df.iloc[0]['total_mv']
    data = {
        'PE': round(pe, 2) if pd.notna(pe) else None,
        'PB': round(pb, 2) if pd.notna(pb) else None,
        '市值(亿)': round(total_mv / 10000, 2) if pd.notna(total_mv) else None
    }
    save_cache(symbol, found_date, data)
    return data