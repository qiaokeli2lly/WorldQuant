import akshare as ak
import baostock as bs
import pandas as pd
import os
import time
import random

# 配置请求间隔（秒）
REQUEST_INTERVAL = (0.5, 1.5)
MAX_RETRIES = 3
BACKOFF_BASE = 2

def get_stock_data(symbol, start_date, end_date, cache_dir="data_cache", max_retries=MAX_RETRIES):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cache_path = os.path.join(script_dir, cache_dir)
    if not os.path.exists(cache_path):
        os.makedirs(cache_path)

    cache_file = os.path.join(cache_path, f"{symbol}.csv")

    # 加载现有缓存
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

    # 辅助函数：填充完整日历
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
        return _fetch_data_with_fallback(s, start_dt, end_dt, max_retries)

    # 已有缓存处理
    if not existing_df.empty:
        existing_start = existing_df.index.min()
        existing_end = existing_df.index.max()
        if existing_start <= start and existing_end >= end:
            # 完全命中，直接返回子集（不打印）
            return existing_df.loc[start:end].copy()
        else:
            new_min = min(existing_start, start)
            new_max = max(existing_end, end)
            new_parts = []

            # 向前扩展
            if start < existing_start:
                missing_start = start.strftime('%Y%m%d')
                missing_end = (existing_start - pd.Timedelta(days=1)).strftime('%Y%m%d')
                part = fetch_trading_data(symbol, missing_start, missing_end)
                if not part.empty:
                    new_parts.append(part)

            # 向后扩展
            if end > existing_end:
                missing_start = (existing_end + pd.Timedelta(days=1)).strftime('%Y%m%d')
                missing_end = end.strftime('%Y%m%d')
                # 单日周末跳过
                if missing_start == missing_end:
                    dt = pd.to_datetime(missing_start)
                    if dt.weekday() >= 5:
                        # 周末，不拉取
                        pass
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


def _fetch_data_with_fallback(symbol, start_date, end_date, max_retries):
    is_single_day = (start_date == end_date)

    for attempt in range(max_retries):
        df = _fetch_from_baostock(symbol, start_date, end_date)
        if not df.empty:
            return df
        if is_single_day:
            break
        if attempt < max_retries - 1:
            wait = (BACKOFF_BASE ** attempt) + random.uniform(0, 1)
            time.sleep(wait)

    df = _fetch_from_akshare(symbol, start_date, end_date, max_retries=1)
    if not df.empty:
        return df
    return pd.DataFrame()


def _fetch_from_akshare(symbol, start_date, end_date, max_retries):
    time.sleep(random.uniform(*REQUEST_INTERVAL))
    df = pd.DataFrame()
    for attempt in range(max_retries):
        try:
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily",
                                    start_date=start_date, end_date=end_date,
                                    adjust="qfq")
            if not df.empty:
                break
        except:
            if attempt < max_retries - 1:
                time.sleep((BACKOFF_BASE ** attempt) + random.uniform(0, 1))
    if df.empty:
        return pd.DataFrame()
    df.rename(columns={'日期':'date','开盘':'open','收盘':'close',
                       '最高':'high','最低':'low','成交量':'volume'}, inplace=True)
    df = df[['date','open','high','low','close','volume']]
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def _fetch_from_baostock(symbol, start_date, end_date):
    # 单日周末直接返回空
    if start_date == end_date:
        dt = pd.to_datetime(start_date)
        if dt.weekday() >= 5:
            return pd.DataFrame()

    time.sleep(random.uniform(*REQUEST_INTERVAL))

    if symbol.startswith('6'):
        bs_code = f"sh.{symbol}"
    elif symbol.startswith('0') or symbol.startswith('3'):
        bs_code = f"sz.{symbol}"
    else:
        return pd.DataFrame()

    start = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
    end = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"

    try:
        bs.login()
        rs = bs.query_history_k_data_plus(bs_code,
                                          fields="date,open,high,low,close,volume",
                                          start_date=start, end_date=end,
                                          frequency="d", adjustflag="2")
        data = []
        while rs.next():
            data.append(rs.get_row_data())
        bs.logout()
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data, columns=['date','open','high','low','close','volume'])
        for col in ['open','high','low','close','volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df['volume'] = df['volume'] / 100
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        return df
    except:
        return pd.DataFrame()


if __name__ == "__main__":
    # 测试单日周末数据（应静默返回空）
    df = get_stock_data("600519", "20220201", "20220201")
    print(df.head())