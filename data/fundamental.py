# data/fundamental.py
import os
import json
import pandas as pd
import numpy as np
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

def get_cache_file(symbol, cache_key):
    return os.path.join(CACHE_DIR, f"{symbol}_{cache_key}.json")

def is_cache_valid(symbol, cache_key, hours=24):
    cache_file = get_cache_file(symbol, cache_key)
    if not os.path.exists(cache_file):
        return False
    mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
    return datetime.now() - mtime < timedelta(hours=hours)

def save_cache(symbol, cache_key, data):
    cache_file = get_cache_file(symbol, cache_key)
    with open(cache_file, 'w') as f:
        json.dump(data, f)

def load_cache(symbol, cache_key):
    cache_file = get_cache_file(symbol, cache_key)
    try:
        with open(cache_file, 'r') as f:
            data = json.load(f)
        # 验证缓存格式：至少有一个键，且所有键都能被解析为日期
        if not data:
            raise ValueError("空缓存")
        for k in data.keys():
            pd.to_datetime(k)  # 尝试转换，失败则抛异常
        return data
    except Exception:
        # 缓存损坏，删除文件并返回 None，下次调用会重新获取
        if os.path.exists(cache_file):
            os.remove(cache_file)
        return None

def safe_float(val):
    try:
        return float(val) if val not in (None, 'None', '') else None
    except:
        return None

# ================== 单股票最新基本面（用于展示） ==================
def get_fundamental_single(symbol):
    if pro is None:
        return None
    ensure_cache_dir()
    if is_cache_valid(symbol, "latest"):
        return load_cache(symbol, "latest")

    ts_code = f"{symbol}.SH" if symbol.startswith('6') else f"{symbol}.SZ"
    result = {}

    try:
        df_basic = pro.daily_basic(ts_code=ts_code, fields='pe_ttm,pb,total_mv', limit=1)
        if not df_basic.empty:
            result['PE'] = safe_float(df_basic.iloc[0].get('pe_ttm'))
            result['PE'] = round(result['PE'], 2) if result['PE'] else None
            result['PB'] = safe_float(df_basic.iloc[0].get('pb'))
            result['PB'] = round(result['PB'], 2) if result['PB'] else None
            total_mv = safe_float(df_basic.iloc[0].get('total_mv'))
            result['市值(亿)'] = round(total_mv / 10000, 2) if total_mv else None

        df_income = pro.income(ts_code=ts_code, fields='revenue,net_profit', limit=1)
        if not df_income.empty:
            revenue = safe_float(df_income.iloc[0].get('revenue'))
            net_profit = safe_float(df_income.iloc[0].get('net_profit'))
            result['营收(亿)'] = round(revenue / 1e8, 2) if revenue else None
            result['净利润(亿)'] = round(net_profit / 1e8, 2) if net_profit else None

        df_bal = pro.balancesheet(ts_code=ts_code, fields='total_liab,total_assets', limit=1)
        if not df_bal.empty and not df_income.empty:
            total_liab = safe_float(df_bal.iloc[0].get('total_liab'))
            total_assets = safe_float(df_bal.iloc[0].get('total_assets'))
            net_profit = safe_float(df_income.iloc[0].get('net_profit')) if not df_income.empty else None
            if total_liab and total_assets and net_profit:
                equity = total_assets - total_liab
                if equity != 0:
                    roe = net_profit / equity
                    result['ROE(%)'] = round(roe * 100, 2)
            result['资产负债率'] = round(total_liab / total_assets, 4) if total_liab and total_assets else None

        df_income_hist = pro.income(ts_code=ts_code, fields='end_date,revenue', limit=2)
        if len(df_income_hist) >= 2:
            df_income_hist = df_income_hist.sort_values('end_date')
            rev_current = safe_float(df_income_hist.iloc[-1].get('revenue'))
            rev_prev = safe_float(df_income_hist.iloc[-2].get('revenue'))
            if rev_prev and rev_prev != 0:
                result['营收同比增长率'] = round((rev_current - rev_prev) / rev_prev, 4)
            else:
                result['营收同比增长率'] = None
        else:
            result['营收同比增长率'] = None

    except Exception as e:
        print(f"获取 {symbol} 基本面失败: {e}")
        return None

    save_cache(symbol, "latest", result)
    return result

# ================== 批量获取指定日期的估值（用于多因子回测） ==================
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
            # 尝试向前查找最近交易日
            for offset in range(1, 10):
                test_date = (pd.to_datetime(trade_date) - timedelta(days=offset)).strftime('%Y%m%d')
                df = pro.daily_basic(ts_code=ts_code_str, trade_date=test_date, fields='ts_code,pe_ttm,pb,total_mv')
                if not df.empty:
                    print(f"向前找到有效交易日: {test_date}")
                    break
        if df.empty:
            print(f"警告: 未找到 {trade_date} 及其附近的有效估值数据")
            return result
        for _, row in df.iterrows():
            ts_code = row['ts_code']
            sym = ts_code.split('.')[0]
            pe = safe_float(row.get('pe_ttm'))
            pb = safe_float(row.get('pb'))
            total_mv = safe_float(row.get('total_mv'))
            data = {
                'PE': round(pe, 2) if pe else None,
                'PB': round(pb, 2) if pb else None,
                '市值(亿)': round(total_mv / 10000, 2) if total_mv else None
            }
            result[sym] = data
            save_cache(sym, trade_date, data)
    except Exception as e:
        print(f"批量获取基本面失败: {e}")
    return result

# ================== 历史价值因子序列（用于回测过滤和图表） ==================
def get_value_factors(symbol, start_date, end_date):
    """
    获取股票在日期范围内的每日价值因子序列
    返回 DataFrame，索引为日期，列包括：PE, PB, 市值(亿), ROE, 毛利率, 净利率, 资产负债率
    """
    if pro is None:
        print("警告: Tushare 未初始化，无法获取价值因子序列")
        return pd.DataFrame()

    ensure_cache_dir()
    cache_key = f"value_{start_date}_{end_date}"
    if is_cache_valid(symbol, cache_key, hours=12):
        data = load_cache(symbol, cache_key)
        if data is not None:
            df = pd.DataFrame(data)
            df.index = pd.to_datetime(df.index)
            df.sort_index(inplace=True)
            return df

    ts_code = f"{symbol}.SH" if symbol.startswith('6') else f"{symbol}.SZ"
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)

    df_daily = pro.daily_basic(ts_code=ts_code, start_date=start_date, end_date=end_date,
                               fields='trade_date,pe_ttm,pb,total_mv')
    if df_daily.empty:
        raise ValueError(f"无法获取 {symbol} 的 daily_basic 数据")
    df_daily['trade_date'] = pd.to_datetime(df_daily['trade_date'])
    df_daily.set_index('trade_date', inplace=True)
    rename_map = {}
    if 'pe_ttm' in df_daily.columns:
        rename_map['pe_ttm'] = 'PE'
    if 'pb' in df_daily.columns:
        rename_map['pb'] = 'PB'
    if 'total_mv' in df_daily.columns:
        rename_map['total_mv'] = '市值(元)'
    df_daily.rename(columns=rename_map, inplace=True)
    for col in ['PE', 'PB', '市值(元)']:
        if col not in df_daily.columns:
            df_daily[col] = np.nan
    df_daily['市值(亿)'] = df_daily['市值(元)'] / 1e8
    df_daily = df_daily[['PE', 'PB', '市值(亿)']]

    # 季度因子
    quarters = []
    current = end
    for _ in range(8):
        quarter_end = pd.Timestamp(year=current.year, month=((current.month-1)//3)*3+3, day=1) + pd.offsets.MonthEnd(0)
        if quarter_end <= end:
            quarters.append(quarter_end)
        current = quarter_end - pd.DateOffset(days=1)
    quarters = sorted(set(quarters))
    quarter_dates = [q.strftime('%Y%m%d') for q in quarters]

    quarter_data = []
    for q_date in quarter_dates:
        try:
            inc = pro.income(ts_code=ts_code, start_date=q_date, end_date=q_date, fields='revenue,net_profit,cost_of_sales')
            bal = pro.balancesheet(ts_code=ts_code, start_date=q_date, end_date=q_date, fields='total_liab,total_assets')
            if inc.empty or bal.empty:
                continue
            revenue = safe_float(inc.iloc[0].get('revenue'))
            net_profit = safe_float(inc.iloc[0].get('net_profit'))
            cost_of_sales = safe_float(inc.iloc[0].get('cost_of_sales'))
            total_liab = safe_float(bal.iloc[0].get('total_liab'))
            total_assets = safe_float(bal.iloc[0].get('total_assets'))
            if revenue is None or net_profit is None or total_liab is None or total_assets is None:
                continue
            equity = total_assets - total_liab
            roe = net_profit / equity if equity != 0 else np.nan
            gross_margin = (revenue - cost_of_sales) / revenue if revenue != 0 else np.nan
            net_margin = net_profit / revenue if revenue != 0 else np.nan
            debt_ratio = total_liab / total_assets if total_assets != 0 else np.nan
            quarter_data.append({
                'date': pd.to_datetime(q_date),
                'ROE': roe * 100,
                '毛利率': gross_margin * 100,
                '净利率': net_margin * 100,
                '资产负债率': debt_ratio * 100
            })
        except:
            continue

    if quarter_data:
        df_quarter = pd.DataFrame(quarter_data).set_index('date')
        full_dates = pd.date_range(start, end, freq='D')
        df_quarter_full = df_quarter.reindex(full_dates, method='ffill')
    else:
        df_quarter_full = pd.DataFrame(index=pd.date_range(start, end, freq='D'))

    combined = df_daily.join(df_quarter_full, how='left')
    combined.ffill(inplace=True)
    # 保存缓存：将索引转换为字符串格式，避免 JSON 序列化问题
    result_dict = combined.to_dict(orient='index')
    save_cache(symbol, cache_key, {k.strftime('%Y-%m-%d'): v for k, v in result_dict.items()})
    return combined

get_fundamental = get_fundamental_single