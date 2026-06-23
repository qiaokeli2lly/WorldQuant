# data/stock_data.py
import tushare as ts
import pandas as pd
import os
import time

# 设置 Tushare token（从环境变量读取，或者直接填入你的token）
TUSHARE_TOKEN = os.environ.get("TUSHARE_TOKEN")
if TUSHARE_TOKEN:
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
else:
    pro = None
    print("警告: TUSHARE_TOKEN 未设置，股票数据无法获取")

REQUEST_INTERVAL = (0.3, 0.8)   # Tushare 免费版频率限制较低，可适当缩短等待
MAX_RETRIES = 3
BACKOFF_BASE = 2

def get_stock_data(symbol, start_date, end_date, cache_dir="data_cache", max_retries=MAX_RETRIES):
    """
    获取 A 股日线数据（前复权），使用 Tushare 接口，带本地缓存。
    symbol: 6位股票代码，如 '600519'
    start_date, end_date: 'YYYYMMDD' 字符串
    """
    if pro is None:
        raise RuntimeError("Tushare pro 未初始化，请检查 TUSHARE_TOKEN 环境变量")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    cache_path = os.path.join(script_dir, cache_dir)
    if not os.path.exists(cache_path):
        os.makedirs(cache_path)

    cache_file = os.path.join(cache_path, f"{symbol}.csv")

    # 加载已有缓存
    existing_df = pd.DataFrame()
    if os.path.exists(cache_file):
        if os.path.getsize(cache_file) == 0:
            os.remove(cache_file)
        else:
            try:
                existing_df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
                if existing_df.empty:
                    os.remove(cache_file)
            except:
                os.remove(cache_file)

    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)

    def fill_to_full_calendar(df, min_date, max_date):
        if df.empty:
            return df
        full_calendar = pd.date_range(min_date, max_date, freq='D')
        df_full = df.reindex(full_calendar)
        df_full.ffill(inplace=True)
        df_full['return'] = df_full['close'].pct_change()
        return df_full

    def safe_save(df, path, min_date, max_date):
        if df is not None and not df.empty:
            df_to_save = fill_to_full_calendar(df, min_date, max_date)
            df_to_save.to_csv(path, date_format='%Y-%m-%d')
            print(f"缓存已保存: {path}，行数: {len(df_to_save)}")
            return True
        return False

    def fetch_trading_data(s, start_dt, end_dt):
        return _fetch_from_tushare(s, start_dt, end_dt, max_retries)

    if not existing_df.empty:
        existing_start = existing_df.index.min()
        existing_end = existing_df.index.max()
        if existing_start <= start and existing_end >= end:
            # 缓存完全覆盖
            return existing_df.loc[start:end].copy()
        else:
            # 缓存部分覆盖，补充缺失区间
            new_min = min(existing_start, start)
            new_max = max(existing_end, end)
            new_parts = []

            if start < existing_start:
                missing_start = start.strftime('%Y%m%d')
                missing_end = (existing_start - pd.Timedelta(days=1)).strftime('%Y%m%d')
                part = fetch_trading_data(symbol, missing_start, missing_end)
                if not part.empty:
                    new_parts.append(part)

            if end > existing_end:
                missing_start = (existing_end + pd.Timedelta(days=1)).strftime('%Y%m%d')
                missing_end = end.strftime('%Y%m%d')
                if missing_start == missing_end:
                    dt = pd.to_datetime(missing_start)
                    if dt.weekday() >= 5:
                        pass   # 周末不请求
                    else:
                        part = fetch_trading_data(symbol, missing_start, missing_end)
                        if not part.empty:
                            new_parts.append(part)
                else:
                    part = fetch_trading_data(symbol, missing_start, missing_end)
                    if not part.empty:
                        new_parts.append(part)

            if not new_parts:
                combined = existing_df
            else:
                combined = pd.concat([existing_df] + new_parts)
                combined = combined[~combined.index.duplicated(keep='last')]
                combined = combined.sort_index()
            safe_save(combined, cache_file, new_min, new_max)
            full_df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            return full_df.loc[start:end].copy()
    else:
        # 无缓存，全新拉取
        df = fetch_trading_data(symbol, start_date, end_date)
        if df.empty:
            return pd.DataFrame()
        safe_save(df, cache_file, start, end)
        full_df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        return full_df.loc[start:end].copy()


def _fetch_from_tushare(symbol, start_date, end_date, max_retries):
    """用 Tushare 获取 A 股日线数据，返回与原来相同格式的 DataFrame"""
    ts_code = f"{symbol}.SH" if symbol.startswith('6') else f"{symbol}.SZ"
    for attempt in range(max_retries):
        try:
            time.sleep(random.uniform(*REQUEST_INTERVAL))
            df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date,
                           fields='trade_date,open,high,low,close,vol')
            if df is not None and not df.empty:
                df = df.rename(columns={
                    'trade_date': 'date',
                    'vol': 'volume'
                })
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date').sort_index()
                df['volume'] = df['volume'] * 100   # Tushare 成交量单位是手，转换为股（与原数据一致）
                df['return'] = df['close'].pct_change()
                return df[['open', 'high', 'low', 'close', 'volume', 'return']]
        except Exception as e:
            print(f"Tushare 获取 {symbol} 失败 (尝试 {attempt+1}): {e}")
            if attempt < max_retries - 1:
                wait = (BACKOFF_BASE ** attempt) + random.uniform(0, 1)
                time.sleep(wait)
    return pd.DataFrame()


import random