# factors/industry_compare.py
import pandas as pd
import numpy as np
import os
from data.data_manager import DataManager
from factors.price_factors import calc_momentum, calc_volatility
import tushare as ts

# 内存缓存：行业名 → [股票代码列表]
_INDUSTRY_MAP = {}
# 内存缓存：股票代码 → 行业名
_SYMBOL_INDUSTRY = {}

def _load_industry_data():
    """服务启动时调用一次，将行业数据加载到内存"""
    global _INDUSTRY_MAP, _SYMBOL_INDUSTRY
    if _INDUSTRY_MAP:  # 已经加载过
        return

    try:
        pro = ts.pro_api()
        df = pro.stock_basic(exchange='', list_status='L', fields='symbol,industry')
        df['symbol'] = df['symbol'].astype(str).str.zfill(6)
        for _, row in df.iterrows():
            sym = row['symbol']
            ind = row['industry']
            if pd.isna(ind) or ind == '':
                continue
            _SYMBOL_INDUSTRY[sym] = ind
            if ind not in _INDUSTRY_MAP:
                _INDUSTRY_MAP[ind] = []
            _INDUSTRY_MAP[ind].append(sym)
        print(f"行业数据加载完成，共 {len(_INDUSTRY_MAP)} 个行业，{len(_SYMBOL_INDUSTRY)} 只股票")
    except Exception as e:
        print(f"加载行业数据失败: {e}")

def get_industry_peers(symbol):
    if not _INDUSTRY_MAP:
        _load_industry_data()
    industry = _SYMBOL_INDUSTRY.get(symbol)
    if not industry:
        return None, []
    peers = _INDUSTRY_MAP.get(industry, [])
    # 最多取15只，避免过多
    return industry, peers[:15]

def industry_compare(symbol):
    dm = DataManager()
    ind, peers = get_industry_peers(symbol)

    end = pd.Timestamp.now().strftime('%Y%m%d')
    start = (pd.Timestamp.now() - pd.DateOffset(months=6)).strftime('%Y%m%d')

    if not ind:
        fund = dm.get_fundamental(symbol) or {}
        df = dm.get_stock_data(symbol, start, end)
        if df.empty:
            return {"error": "行情数据获取失败"}
        close = df['close']
        mom = calc_momentum(close, 20)
        vol = abs(calc_volatility(close, 20)) if not pd.isna(calc_volatility(close, 20)) else None
        return {
            "symbol": symbol,
            "industry": "未分类",
            "note": "该股票未在行业分类中，仅展示自身指标",
            "comparisons": [{
                "symbol": symbol,
                "pe": fund.get('PE'),
                "pb": fund.get('PB'),
                "momentum": round(mom, 4) if not pd.isna(mom) else None,
                "volatility": round(vol, 4) if vol and not pd.isna(vol) else None,
                "momentum_rank": None, "pe_rank": None, "pb_rank": None
            }]
        }

    results = {"symbol": symbol, "industry": ind, "comparisons": []}
    for peer in peers:
        fund = dm.get_fundamental(peer)
        if not fund:
            continue
        df = dm.get_stock_data(peer, start, end)
        if df.empty:
            continue
        close = df['close']
        mom = calc_momentum(close, 20)
        vol = abs(calc_volatility(close, 20)) if not pd.isna(calc_volatility(close, 20)) else None
        results["comparisons"].append({
            "symbol": peer,
            "pe": fund.get('PE'),
            "pb": fund.get('PB'),
            "momentum": round(mom, 4) if not pd.isna(mom) else None,
            "volatility": round(vol, 4) if vol and not pd.isna(vol) else None
        })

    if not results["comparisons"]:
        return {"error": "无同行数据"}

    df_comp = pd.DataFrame(results["comparisons"])
    if 'momentum' in df_comp.columns and df_comp['momentum'].notna().any():
        df_comp['momentum_rank'] = df_comp['momentum'].rank(ascending=False)
    if 'pe' in df_comp.columns and df_comp['pe'].notna().any():
        df_comp['pe_rank'] = df_comp['pe'].rank()
    if 'pb' in df_comp.columns and df_comp['pb'].notna().any():
        df_comp['pb_rank'] = df_comp['pb'].rank()
    results["comparisons"] = df_comp.to_dict(orient='records')
    return results