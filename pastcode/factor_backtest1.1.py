"""
multi_factor_backtest.py
完整多因子选股回测系统（baostock 基本面，修复字段解析，统一登录）
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings
import os
import json
import time
import random
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from tqdm import tqdm
import baostock as bs

from data_utils import get_stock_data

warnings.filterwarnings('ignore')

# ================== 配置 ==================
START_DATE = "20220101"
END_DATE = "20241231"
TOP_N = 20
REBALANCE_FREQ = 'M'
RISK_FREE_RATE = 0.03

# 因子列表（包含基本面）
FACTORS = ['momentum', 'reversal', 'volatility', 'turnover', 'volume_ratio', 'pb', 'roe']
WEIGHTS = {f: 1/len(FACTORS) for f in FACTORS}

# 基本面缓存目录
FUND_CACHE_DIR = "fundamental_cache"

def ensure_cache_dir():
    os.makedirs(FUND_CACHE_DIR, exist_ok=True)

# ================== 股票池 ==================
def get_stock_pool():
    return [
        '600519', '000858', '601318', '600036', '000333',
        '002415', '300750', '601888', '600900', '601166',
        '000002', '002594', '600276', '601398', '600030',
        '601288', '600887', '601628', '000001', '002352',
        '600309', '601012', '600585', '000568', '002714',
        '300059', '601818', '600048', '601688', '600104'
    ]

# ================== baostock 基本面获取（带缓存）==================
def get_bs_code(symbol):
    if symbol.startswith('6'):
        return f"sh.{symbol}"
    elif symbol.startswith('0') or symbol.startswith('3'):
        return f"sz.{symbol}"
    return None

def get_pb_baostock(bs_code, target_date):
    """获取指定日期最近一个交易日的 PB"""
    # 向前查找最多10个交易日
    for offset in range(10):
        query_date = (target_date - timedelta(days=offset)).strftime('%Y-%m-%d')
        rs = bs.query_history_k_data_plus(bs_code, "date,pbMRQ",
                                          start_date=query_date, end_date=query_date,
                                          frequency="d", adjustflag="2")
        if rs.error_code == '0' and rs.next():
            row = rs.get_row_data()
            if len(row) > 1 and row[1] and row[1] != '':
                return float(row[1])
    return np.nan

def get_roe_baostock(bs_code, year, quarter):
    """获取指定季度的 ROE（平均）"""
    rs = bs.query_profit_data(code=bs_code, year=year, quarter=quarter)
    if rs.error_code == '0':
        # fields 可能是列表或字符串
        fields = rs.fields
        if isinstance(fields, str):
            fields = fields.split(',')
        try:
            idx = fields.index('roeAvg')
        except ValueError:
            idx = 3  # 常见位置
        if rs.next():
            row = rs.get_row_data()
            if len(row) > idx and row[idx] and row[idx] != '':
                return float(row[idx]) / 100.0   # 转为小数
    return np.nan

def get_fundamental(symbol, date):
    """获取指定股票在指定日期的 PB 和 ROE（带文件缓存）"""
    ensure_cache_dir()
    date_str = pd.to_datetime(date).strftime('%Y%m%d')
    cache_file = os.path.join(FUND_CACHE_DIR, f"{symbol}_{date_str}.json")
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            data = json.load(f)
        return data.get('pb', np.nan), data.get('roe', np.nan)

    bs_code = get_bs_code(symbol)
    if bs_code is None:
        return np.nan, np.nan

    target_date = pd.to_datetime(date)
    pb = get_pb_baostock(bs_code, target_date)
    year = target_date.year
    quarter = (target_date.month - 1) // 3 + 1
    roe = get_roe_baostock(bs_code, year, quarter)

    with open(cache_file, 'w') as f:
        json.dump({'pb': pb, 'roe': roe, 'symbol': symbol, 'date': date_str}, f)
    return pb, roe

# ================== 量价因子 ==================
def calc_momentum(df, lookback=20):
    return df['close'].pct_change(lookback)

def calc_reversal(df, lookback=5):
    return -df['close'].pct_change(lookback)

def calc_volatility(df, lookback=20):
    vol = df['close'].pct_change().rolling(lookback).std()
    return -vol

def calc_turnover(df, lookback=20):
    vol_ma = df['volume'].rolling(lookback).mean()
    return df['volume'] / vol_ma

def calc_volume_ratio(df, lookback=20):
    vol_5 = df['volume'].rolling(5).mean()
    vol_20 = df['volume'].rolling(lookback).mean()
    return vol_5 / vol_20

# ================== 获取单日因子数据 ==================
def get_factor_data(date, stock_list, lookbacks, use_fundamental=True):
    factor_dict = {f: [] for f in FACTORS}
    stocks_valid = []
    for stock in tqdm(stock_list, desc=f"  处理 {date.date()}", leave=False):
        hist_start = (date - pd.Timedelta(days=max(lookbacks.values())+60)).strftime('%Y%m%d')
        hist_end = date.strftime('%Y%m%d')
        df = get_stock_data(stock, hist_start, hist_end)
        if df.empty or len(df) < max(lookbacks.values()):
            continue
        try:
            mom = calc_momentum(df, lookbacks['momentum']).iloc[-1]
            rev = calc_reversal(df, lookbacks['reversal']).iloc[-1]
            vol = calc_volatility(df, lookbacks['volatility']).iloc[-1]
            turn = calc_turnover(df, lookbacks['turnover']).iloc[-1]
            vr = calc_volume_ratio(df, lookbacks['volume_ratio']).iloc[-1]
        except:
            continue
        if any(np.isnan(v) for v in [mom, rev, vol, turn, vr]):
            continue
        pb, roe = np.nan, np.nan
        if use_fundamental:
            pb, roe = get_fundamental(stock, date)
        # 若基本面缺失，跳过（可根据需要调整）
        if use_fundamental and (np.isnan(pb) or np.isnan(roe)):
            continue
        stocks_valid.append(stock)
        factor_dict['momentum'].append(mom)
        factor_dict['reversal'].append(rev)
        factor_dict['volatility'].append(vol)
        factor_dict['turnover'].append(turn)
        factor_dict['volume_ratio'].append(vr)
        factor_dict['pb'].append(pb)
        factor_dict['roe'].append(roe)

    if not stocks_valid:
        return pd.DataFrame()
    return pd.DataFrame(factor_dict, index=stocks_valid)

# ================== 因子预处理 ==================
def winsorize_series(series, limit=0.01):
    lower = series.quantile(limit)
    upper = series.quantile(1 - limit)
    return series.clip(lower, upper)

def standardize_series(series):
    return (series - series.mean()) / series.std()

def process_factors(factor_df):
    df = factor_df.copy()
    for col in FACTORS:
        if col in df.columns:
            df[col] = winsorize_series(df[col])
            df[col] = standardize_series(df[col])
    return df

# ================== 多因子合成 ==================
def combine_factors(factor_df, weights):
    score = pd.Series(0, index=factor_df.index)
    for col, w in weights.items():
        if col in factor_df.columns:
            score += factor_df[col] * w
    return score

# ================== 主回测函数 ==================
def multi_factor_backtest(start_date, end_date, top_n=TOP_N, use_fundamental=True):
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)

    stock_list = get_stock_pool()
    print(f"股票池大小: {len(stock_list)}")

    # 生成调仓日期（月末）
    all_dates = pd.date_range(start, end, freq='D')
    month_end_dates = [d for d in all_dates if d + pd.offsets.MonthEnd(0) == d]
    rebalance_dates = [d for d in month_end_dates if start <= d <= end]
    print(f"调仓次数: {len(rebalance_dates)}")

    lookbacks = {
        'momentum': 20,
        'reversal': 5,
        'volatility': 20,
        'turnover': 20,
        'volume_ratio': 20
    }

    # 登录 baostock（全局一次）
    lg = bs.login()
    print(f"baostock 登录: {lg.error_msg}")
    if lg.error_code != '0':
        print("登录失败，退出")
        return

    daily_nav = pd.Series(1.0, index=pd.date_range(start, end, freq='D'))
    trade_log = []
    current_holdings = []

    for i, rebal_date in enumerate(tqdm(rebalance_dates, desc="回测进度")):
        factor_df = get_factor_data(rebal_date, stock_list, lookbacks, use_fundamental)
        if factor_df.empty:
            continue
        factor_df = process_factors(factor_df)
        score = combine_factors(factor_df, WEIGHTS)
        selected = score.nlargest(top_n).index.tolist()

        if i == 0:
            for s in selected:
                trade_log.append({'调仓日期': rebal_date.strftime('%Y-%m-%d'), '股票代码': s, '操作': '买入'})
        else:
            for s in current_holdings:
                if s not in selected:
                    trade_log.append({'调仓日期': rebal_date.strftime('%Y-%m-%d'), '股票代码': s, '操作': '卖出'})
            for s in selected:
                if s not in current_holdings:
                    trade_log.append({'调仓日期': rebal_date.strftime('%Y-%m-%d'), '股票代码': s, '操作': '买入'})
        current_holdings = selected

        if i+1 < len(rebalance_dates):
            next_start = rebal_date + pd.Timedelta(days=1)
            next_end = rebalance_dates[i+1]
        else:
            next_start = rebal_date + pd.Timedelta(days=1)
            next_end = end
        date_range = pd.date_range(next_start, next_end, freq='D')
        for dt in date_range:
            daily_ret = 0
            cnt = 0
            for stock in selected:
                df_day = get_stock_data(stock, dt.strftime('%Y%m%d'), dt.strftime('%Y%m%d'))
                if not df_day.empty and 'return' in df_day.columns:
                    ret = df_day['return'].iloc[0]
                    if not np.isnan(ret):
                        daily_ret += ret
                        cnt += 1
            if cnt > 0:
                daily_ret /= cnt
            prev_nav = daily_nav[daily_nav.index < dt].iloc[-1] if len(daily_nav[daily_nav.index < dt]) > 0 else 1.0
            daily_nav[dt] = prev_nav * (1 + daily_ret)

    bs.logout()

    benchmark = get_stock_data("000300", start_date, end_date)
    if not benchmark.empty:
        benchmark_nav = (1 + benchmark['return']).cumprod()
        benchmark_nav = benchmark_nav.reindex(daily_nav.index, method='ffill').fillna(1)
    else:
        benchmark_nav = pd.Series(1.0, index=daily_nav.index)

    daily_nav = daily_nav.fillna(1)
    total_days = len(daily_nav.dropna())
    years = total_days / 252
    total_return = daily_nav.iloc[-1] - 1
    annual_return = (1 + total_return) ** (1/years) - 1 if years > 0 else 0
    cummax = daily_nav.cummax()
    max_drawdown = (daily_nav - cummax).min()
    daily_returns = daily_nav.pct_change().dropna()
    sharpe = (annual_return - RISK_FREE_RATE) / (daily_returns.std() * np.sqrt(252)) if daily_returns.std() != 0 else np.nan
    excess = daily_nav / benchmark_nav - 1
    total_excess = excess.iloc[-1] if not excess.empty else 0

    metrics = {
        '年化收益率': annual_return,
        '累计收益率': total_return,
        '最大回撤': max_drawdown,
        '夏普比率': sharpe,
        '累计超额收益': total_excess,
        '交易次数': len(trade_log)
    }
    trade_df = pd.DataFrame(trade_log) if trade_log else pd.DataFrame()
    return daily_nav, benchmark_nav, metrics, trade_df

def plot_results(portfolio_nav, benchmark_nav):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
    ax1.plot(portfolio_nav.index, portfolio_nav, label='策略净值')
    ax1.plot(benchmark_nav.index, benchmark_nav, label='基准净值')
    ax1.legend()
    ax1.grid()
    excess = portfolio_nav / benchmark_nav - 1
    ax2.fill_between(excess.index, 0, excess, where=(excess>=0), color='green', alpha=0.3)
    ax2.fill_between(excess.index, 0, excess, where=(excess<0), color='red', alpha=0.3)
    ax2.plot(excess.index, excess, color='black')
    ax2.axhline(0, linestyle='--')
    ax2.set_ylabel('超额收益')
    plt.tight_layout()
    plt.show()

def save_results_to_excel(filepath, metrics, trade_df, portfolio_nav, benchmark_nav):
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        pd.DataFrame(metrics.items(), columns=['指标', '数值']).to_excel(writer, sheet_name='绩效', index=False)
        if not trade_df.empty:
            trade_df.to_excel(writer, sheet_name='交易明细', index=False)
        nav_df = pd.DataFrame({'策略净值': portfolio_nav, '基准净值': benchmark_nav})
        nav_df.resample('M').last().to_excel(writer, sheet_name='月度净值')
    print(f"报告保存至 {filepath}")

if __name__ == "__main__":
    # 先测试只用基本面？建议先 use_fundamental=False 跑通量价部分
    nav, bench, metrics, trades = multi_factor_backtest(START_DATE, END_DATE, use_fundamental=False)
    print("\n绩效报告:")
    for k, v in metrics.items():
        print(f"{k}: {v:.4f}" if isinstance(v, float) else f"{k}: {v}")
    plot_results(nav, bench)
    save_results_to_excel("multi_factor_report.xlsx", metrics, trades, nav, bench)