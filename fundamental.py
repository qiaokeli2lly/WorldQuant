"""
fundamental.py
基于 Tushare 批量接口获取股票估值数据（PE、PB、市值），带本地缓存
支持：
- 获取单个股票最新一期估值
- 获取单个股票历史区间估值（每日）
"""

import os
import pandas as pd
import tushare as ts
from datetime import datetime, timedelta

# ================== 配置 ==================
CACHE_DIR = "fundamental_cache"
TUSHARE_TOKEN = os.environ.get("TUSHARE_TOKEN")
if not TUSHARE_TOKEN:
    raise ValueError("请设置环境变量 TUSHARE_TOKEN")

ts.set_token(TUSHARE_TOKEN)
pro = ts.pro_api()

# ================== 辅助函数 ==================
def ensure_cache_dir():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

def get_cache_path(ts_code, start_date, end_date):
    """生成缓存文件路径，例如: fundamental_cache/600519.SH_20240201_20240229.csv"""
    filename = f"{ts_code}_{start_date}_{end_date}.csv"
    return os.path.join(CACHE_DIR, filename)

def load_cache(cache_path):
    if os.path.exists(cache_path):
        return pd.read_csv(cache_path)
    return None

def save_cache(df, cache_path):
    df.to_csv(cache_path, index=False)
    print(f"缓存已保存: {cache_path}")

def get_last_trading_date():
    """获取最近一个交易日（昨天或往前找）"""
    for offset in range(1, 10):
        test_date = (datetime.now() - timedelta(days=offset)).strftime('%Y%m%d')
        # 用任意一只股票测试是否有数据
        df = pro.daily_basic(ts_code='600519.SH', trade_date=test_date, fields='ts_code')
        if not df.empty:
            return test_date
    raise ValueError("无法找到有效交易日")

# ================== 核心获取函数 ==================
def get_valuation_range(ts_code, start_date, end_date, force_refresh=False):
    """
    批量获取指定股票在日期范围内的每日估值数据
    ts_code: 例如 '600519.SH'
    start_date, end_date: 格式 'YYYYMMDD'
    force_refresh: 是否强制刷新缓存
    返回 DataFrame，列: trade_date, pe_ttm, pb, total_mv
    """
    ensure_cache_dir()
    cache_path = get_cache_path(ts_code, start_date, end_date)

    if not force_refresh:
        df_cache = load_cache(cache_path)
        if df_cache is not None:
            print(f"从缓存读取: {cache_path}")
            return df_cache

    print(f"从 Tushare 获取 {ts_code} {start_date}~{end_date}")
    try:
        df = pro.daily_basic(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields='trade_date,pe_ttm,pb,total_mv'
        )
        if df.empty:
            print("警告: 无数据")
            return pd.DataFrame()
        # 类型转换
        for col in ['pe_ttm', 'pb', 'total_mv']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        save_cache(df, cache_path)
        return df
    except Exception as e:
        print(f"获取失败: {e}")
        return pd.DataFrame()

def get_fundamental(symbol, force_refresh=False):
    """
    获取单只股票的最新一期估值数据（PE、PB、市值）
    symbol: 6位数字代码，如 '600519'
    返回 dict: {'PE': xx, 'PB': xx, '市值(亿)': xx}
    """
    ts_code = f"{symbol}.SH" if symbol.startswith('6') else f"{symbol}.SZ"
    # 获取最近交易日
    trade_date = get_last_trading_date()
    # 获取该日数据（通过批量接口单日范围）
    df = get_valuation_range(ts_code, trade_date, trade_date, force_refresh=force_refresh)
    if df.empty:
        return None
    row = df.iloc[0]
    pe = row['pe_ttm']
    pb = row['pb']
    total_mv = row['total_mv']  # 单位万元
    return {
        'PE': round(pe, 2) if pd.notna(pe) else None,
        'PB': round(pb, 2) if pd.notna(pb) else None,
        '市值(亿)': round(total_mv / 10000, 2) if pd.notna(total_mv) else None
    }

# ================== 测试代码 ==================
if __name__ == "__main__":
    # 测试最新估值
    symbols = ["600519", "000858", "600900"]
    print("测试最新估值获取：")
    for sym in symbols:
        data = get_fundamental(sym)
        print(f"{sym}: {data}")

    # 测试历史区间批量获取（600900 2024年2月）
    print("\n测试历史区间批量获取（600900 2024年2月）：")
    df_hist = get_valuation_range("600900.SH", "20240201", "20240229")
    if not df_hist.empty:
        print(df_hist.to_string(index=False))
    else:
        print("无数据")