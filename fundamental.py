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
            return json.load(f)
    except:
        return None

def safe_float(val):
    try:
        return float(val) if val not in (None, 'None', '') else None
    except:
        return None

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

def get_value_factors(symbol, start_date, end_date):
    if pro is None:
        raise ValueError("Tushare 未初始化")
    ensure_cache_dir()
    cache_key = f"value_{start_date}_{end_date}"
    if is_cache_valid(symbol, cache_key, hours=12):
        data = load_cache(symbol, cache_key)
        if data is not None:
            # 从缓存恢复 DataFrame
            df = pd.DataFrame(data).T
            df.index = pd.to_datetime(df.index, format='%Y-%m-%d')
            return df.sort_index()

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
    result_dict = combined.to_dict(orient='index')
    save_cache(symbol, cache_key, {k.strftime('%Y-%m-%d'): v for k, v in result_dict.items()})
    return combined

get_fundamental = get_fundamental_single