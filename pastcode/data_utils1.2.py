import akshare as ak
import baostock as bs
import pandas as pd
import os
import time
import random

def get_stock_data(symbol, start_date, end_date, cache_dir="data_cache", max_retries=3):
    """
    获取 A 股日线数据，缓存中包含连续日历日期，非交易日用前一天数据填充
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cache_path = os.path.join(script_dir, cache_dir)
    if not os.path.exists(cache_path):
        os.makedirs(cache_path)
        print(f"创建缓存文件夹: {cache_path}")

    cache_file = os.path.join(cache_path, f"{symbol}.csv")

    # ---- 加载现有缓存 ----
    existing_df = pd.DataFrame()
    if os.path.exists(cache_file):
        if os.path.getsize(cache_file) == 0:
            print(f"缓存文件 {cache_file} 为空，将重新拉取。")
            os.remove(cache_file)
        else:
            try:
                existing_df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
                if existing_df.empty:
                    print(f"缓存文件 {cache_file} 无数据，将重新拉取。")
                    os.remove(cache_file)
                else:
                    print(f"从缓存加载 {symbol}，行数: {len(existing_df)}，日期范围: {existing_df.index.min()} 至 {existing_df.index.max()}")
            except Exception as e:
                print(f"读取缓存失败: {e}，将重新拉取。")
                os.remove(cache_file)
    else:
        print(f"未找到缓存文件 {cache_file}，将全新拉取。")

    # ---- 请求的完整日期范围 ----
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    requested_dates = pd.date_range(start, end, freq='D')
    print(f"请求日期范围: {start.date()} 至 {end.date()}，共 {len(requested_dates)} 天")

    # ---- 辅助函数：将交易日数据转为完整日历并填充前值 ----
    def fill_to_full_calendar(df, min_date, max_date):
        if df.empty:
            return df
        full_calendar = pd.date_range(min_date, max_date, freq='D')
        df_full = df.reindex(full_calendar)
        df_full.ffill(inplace=True)
        df_full['return'] = df_full['close'].pct_change()
        return df_full

    # ---- 安全保存缓存 ----
    def safe_save(df, path, min_date, max_date):
        if df is not None and not df.empty:
            df_to_save = fill_to_full_calendar(df, min_date, max_date)
            df_to_save.to_csv(path, date_format='%Y-%m-%d')
            print(f"缓存已保存: {path}，行数: {len(df_to_save)}")
            return True
        else:
            print(f"警告：DataFrame 为空，跳过保存 {path}")
            return False

    # ---- 拉取指定日期范围的交易日数据（仅交易日，未填充）----
    def fetch_trading_data(s, start_dt, end_dt):
        return _fetch_data_with_fallback(s, start_dt, end_dt, max_retries)

    # ---- 情况1：已有缓存 ----
    if not existing_df.empty:
        existing_start = existing_df.index.min()
        existing_end = existing_df.index.max()
        req_start = start
        req_end = end

        if existing_start <= req_start and existing_end >= req_end:
            print("请求范围已完全在缓存中，直接返回子集（已填充连续日期）。")
            return existing_df.loc[start:end].copy()
        else:
            new_min = min(existing_start, req_start)
            new_max = max(existing_end, req_end)
            print(f"缓存范围需要扩展至: {new_min.date()} 至 {new_max.date()}")

            new_parts = []
            # 处理更早日期
            if req_start < existing_start:
                missing_start = req_start.strftime('%Y%m%d')
                missing_end = (existing_start - pd.Timedelta(days=1)).strftime('%Y%m%d')
                # 检查缺失区间是否全是周末？简化处理，仍拉取，因为可能包含交易日
                print(f"拉取更早数据: {missing_start} 至 {missing_end}")
                part = fetch_trading_data(symbol, missing_start, missing_end)
                if not part.empty:
                    new_parts.append(part)

            # 处理更晚日期
            if req_end > existing_end:
                missing_start = (existing_end + pd.Timedelta(days=1)).strftime('%Y%m%d')
                missing_end = req_end.strftime('%Y%m%d')
                # 检查缺失区间是否全是周末（仅处理单日周末）
                is_weekend_only = False
                if missing_start == missing_end:
                    dt = pd.to_datetime(missing_start)
                    if dt.weekday() >= 5:  # 周六或周日
                        is_weekend_only = True
                if is_weekend_only:
                    print(f"缺失日期 {missing_start} 为周末，无需拉取，将用前值填充")
                    # 不添加任何 part，直接跳过拉取
                else:
                    print(f"拉取更晚数据: {missing_start} 至 {missing_end}")
                    part = fetch_trading_data(symbol, missing_start, missing_end)
                    if not part.empty:
                        new_parts.append(part)

            if not new_parts and existing_df is not None:
                # 如果没有拉取到任何新数据，但我们需要扩展缓存范围（例如只有周末缺失）
                # 此时仍然需要保存缓存，以便将缺失的周末日期填充进缓存
                # 直接使用 existing_df 作为 combined，然后 safe_save 会将其扩展到 new_max
                combined = existing_df
                print("没有拉取到新数据，但将扩展缓存范围（填充周末）")
            else:
                combined = pd.concat([existing_df] + new_parts)
                combined = combined[~combined.index.duplicated(keep='last')]
                combined = combined.sort_index()
                print(f"合并后交易日数据行数: {len(combined)}")

            safe_save(combined, cache_file, new_min, new_max)
            full_df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            return full_df.loc[start:end].copy()
    else:
        # ---- 情况2：无缓存，全新拉取 ----
        print(f"全新拉取 {symbol} {start_date} 至 {end_date} 的交易日数据")
        df = fetch_trading_data(symbol, start_date, end_date)
        if df.empty:
            print("错误：无法获取数据。")
            return pd.DataFrame()
        safe_save(df, cache_file, start, end)
        full_df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        return full_df.loc[start:end].copy()


def _fetch_data_with_fallback(symbol, start_date, end_date, max_retries=3):
    """
    优先使用 baostock，失败时根据情况重试或切换 akshare
    对于单日请求且 baostock 返回空数据，直接放弃，不再重试
    """
    is_single_day = (start_date == end_date)

    # 1. 尝试 baostock
    for attempt in range(max_retries):
        df = _fetch_from_baostock(symbol, start_date, end_date)
        if not df.empty:
            # print("使用 baostock 获取数据成功")
            return df
        else:
            if is_single_day:
                # 单日无数据（可能是周末或停牌），不再重试
                break
            else:
                # print(f"baostock 第 {attempt+1} 次尝试失败，返回空数据")
                if attempt < max_retries - 1:
                    time.sleep((2 ** attempt) + random.uniform(0, 1))

    # 2. baostock 失败，尝试 akshare（仅尝试一次）
    # print("baostock 失败，尝试切换到 akshare...")
    df = _fetch_from_akshare(symbol, start_date, end_date, max_retries=1)
    if not df.empty:
        # print("使用 akshare 获取数据成功")
        return df
    else:
        # print("两个数据源均未能获取到数据")
        return pd.DataFrame()


def _fetch_from_akshare(symbol, start_date, end_date, max_retries):
    """AKShare 拉取，单位：手，单日空数据也仅尝试一次"""
    df = pd.DataFrame()
    for attempt in range(max_retries):
        try:
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily",
                                    start_date=start_date, end_date=end_date,
                                    adjust="qfq")
            if not df.empty:
                break
        except Exception as e:
            # print(f"AKShare 第 {attempt+1} 次失败: {e}")
            if attempt < max_retries - 1:
                time.sleep((2 ** attempt) + random.uniform(0, 1))
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
    """
    从 baostock 拉取数据，返回交易日数据（未填充）。
    对于单日周末请求直接返回空 DataFrame，不进行网络查询。
    """
    # 如果是单日请求且为周末，直接返回空
    if start_date == end_date:
        dt = pd.to_datetime(start_date)
        if dt.weekday() >= 5:  # 5=周六, 6=周日
            return pd.DataFrame()

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
        df['volume'] = df['volume'] / 100   # 股转手
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        return df
    except Exception as e:
        print(f"baostock 异常: {e}")
        return pd.DataFrame()


if __name__ == "__main__":
    # 测试：拉取单日周末数据（应直接返回空，不请求网络）
    df = get_stock_data("300059", "20220201", "20220201")
    print(df)