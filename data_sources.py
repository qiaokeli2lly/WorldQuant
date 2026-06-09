# intelligence/data_sources.py
import tushare as ts
import pandas as pd
from datetime import datetime

def convert_code(symbol):
    """将 600519 转换为 600519.SH / 000858.SZ"""
    if symbol.startswith('6'):
        return f"{symbol}.SH"
    else:
        return f"{symbol}.SZ"

def get_news(symbol, start_date, end_date, limit=20):
    """获取个股新闻（需要2000积分以上权限）"""
    pro = ts.pro_api()
    try:
        df = pro.news(ts_code=convert_code(symbol),
                      start_date=start_date,
                      end_date=end_date,
                      limit=limit)
        if df is not None and not df.empty:
            return df[['datetime', 'content', 'title']]
        return pd.DataFrame()
    except Exception as e:
        print(f"获取新闻失败: {e}")
        return pd.DataFrame()

def get_announcements(symbol, start_date, end_date, limit=10):
    """获取个股公告（需要2000积分以上权限）"""
    pro = ts.pro_api()
    try:
        df = pro.disclosure(ts_code=convert_code(symbol),
                            start_date=start_date,
                            end_date=end_date,
                            limit=limit)
        if df is not None and not df.empty:
            return df[['ann_date', 'title']]
        return pd.DataFrame()
    except Exception as e:
        print(f"获取公告失败: {e}")
        return pd.DataFrame()

def get_moneyflow(symbol, start_date, end_date):
    """获取个股资金流向"""
    pro = ts.pro_api()
    try:
        df = pro.moneyflow(ts_code=convert_code(symbol),
                           start_date=start_date,
                           end_date=end_date)
        return df if not df.empty else pd.DataFrame()
    except Exception as e:
        print(f"获取资金流向失败: {e}")
        return pd.DataFrame()

def get_concept(symbol):
    """获取所属概念板块"""
    pro = ts.pro_api()
    try:
        df = pro.concept_detail(ts_code=convert_code(symbol))
        if df is not None and not df.empty:
            return df['concept_name'].tolist()
        return []
    except Exception as e:
        print(f"获取概念失败: {e}")
        return []
        # 添加到 intelligence/data_sources.py 文件末尾

import os
import json
from datetime import datetime, timedelta

# 股票名称缓存文件
STOCK_NAME_CACHE = "stock_name_cache.json"

def _load_name_cache():
    if os.path.exists(STOCK_NAME_CACHE):
        with open(STOCK_NAME_CACHE, 'r') as f:
            return json.load(f)
    return {}

def _save_name_cache(cache_dict):
    with open(STOCK_NAME_CACHE, 'w') as f:
        json.dump(cache_dict, f)

def get_stock_name(symbol):
    """
    根据股票代码获取股票名称，带本地缓存。
    若无法获取，返回空字符串。
    """
    cache = _load_name_cache()
    if symbol in cache:
        return cache[symbol]

    try:
        pro = ts.pro_api()
        # 查询 stock_basic
        ts_code = convert_code(symbol)
        df = pro.stock_basic(ts_code=ts_code, fields='name')
        if df is not None and not df.empty:
            name = df.iloc[0]['name']
            cache[symbol] = name
            _save_name_cache(cache)
            return name
    except Exception as e:
        print(f"获取股票名称失败: {e}")
    return ""