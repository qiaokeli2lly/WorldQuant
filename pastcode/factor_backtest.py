"""
multi_factor_backtest.py
修正调用逻辑：预加载全量数据，确保缓存完整，回测高效稳定
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings
from tqdm import tqdm
from data_utils import get_stock_data

warnings.filterwarnings('ignore')

# ================== 配置 ==================
START_DATE = "20220101"
END_DATE = "20241231"
TOP_N = 20
RISK_FREE_RATE = 0.03

# 股票池
STOCK_POOL = [
    '600519', '000858', '601318', '600036', '000333',
    '002415', '300750', '601888', '600900', '601166',
    '000002', '002594', '600276', '601398', '600030',
    '601288', '600887', '601628', '000001', '002352',
    '600309', '601012', '600585', '000568', '002714',
    '300059', '601818', '600048', '601688', '600104'
]

# ================== 预加载所有股票全量数据 ==================
def preload_all_data(stock_list, start_date, end_date):
    """强制缓存整个回测区间数据，确保后续读取直接从缓存"""
    print("预加载全量数据，确保缓存完整...")
    for stock in tqdm(stock_list, desc="预加载进度"):
        get_stock_data(stock, start_date, end_date)
    print("预加载完成。")

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

# ================== 获取单日因子数据（直接从缓存读取）==================
def get_factor_data(date, stock_list, lookbacks):
    """
    返回 DataFrame: index=股票代码, columns=因子名称
    使用预加载后的缓存，快速获取数据
    """
    factors = ['momentum', 'reversal', 'volatility', 'turnover', 'volume_ratio']
    factor_dict = {f: [] for f in factors}
    stocks_valid = []

    # 计算所需的起始日期（最大回看窗口 + 缓冲）
    max_lookback = max(lookbacks.values())
    hist_start = (date - pd.Timedelta(days=max_lookback + 10)).strftime('%Y%m%d')
    hist_end = date.strftime('%Y%m%d')

    for stock in tqdm(stock_list, desc=f"  因子计算 {date.date()}", leave=False):
        df = get_stock_data(stock, hist_start, hist_end)
        if df.empty or len(df) < max_lookback:
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

        stocks_valid.append(stock)
        factor_dict['momentum'].append(mom)
        factor_dict['reversal'].append(rev)
        factor_dict['volatility'].append(vol)
        factor_dict['turnover'].append(turn)
        factor_dict['volume_ratio'].append(vr)

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
    for col in df.columns:
        df[col] = winsorize_series(df[col])
        df[col] = standardize_series(df[col])
    return df

def combine_factors(factor_df):
    # 等权合成
    return factor_df.mean(axis=1)

# ================== 主回测函数 ==================
def multi_factor_backtest(start_date, end_date, top_n=TOP_N):
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    stock_list = STOCK_POOL
    print(f"股票池大小: {len(stock_list)}")

    # 预加载全量数据（强制填充缓存）
    preload_all_data(stock_list, start_date, end_date)

    # 生成调仓日期（月末）
    all_dates = pd.date_range(start, end, freq='D')
    rebalance_dates = [d for d in all_dates if d.is_month_end]
    print(f"调仓次数: {len(rebalance_dates)}")
    print("调仓日期:", [d.strftime('%Y-%m-%d') for d in rebalance_dates])

    lookbacks = {
        'momentum': 20,
        'reversal': 5,
        'volatility': 20,
        'turnover': 20,
        'volume_ratio': 20
    }

    daily_nav = pd.Series(1.0, index=pd.date_range(start, end, freq='D'))
    trade_log = []
    current_holdings = []

    for i, rebal_date in enumerate(tqdm(rebalance_dates, desc="回测进度")):
        print(f"\n调仓日: {rebal_date.date()}")
        factor_df = get_factor_data(rebal_date, stock_list, lookbacks)
        if factor_df.empty:
            print("  无有效因子数据，跳过本次调仓")
            continue

        factor_df = process_factors(factor_df)
        score = combine_factors(factor_df)
        selected = score.nlargest(top_n).index.tolist()
        print(f"  选中股票: {selected[:5]}... 共{len(selected)}只")

        # 记录调仓操作
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

        # 计算组合下个期间的每日净值
        if i + 1 < len(rebalance_dates):
            period_start = rebal_date + pd.Timedelta(days=1)
            period_end = rebalance_dates[i+1]
        else:
            period_start = rebal_date + pd.Timedelta(days=1)
            period_end = end
        period_dates = pd.date_range(period_start, period_end, freq='D')
        for dt in period_dates:
            daily_ret = 0
            count = 0
            for stock in selected:
                df_day = get_stock_data(stock, dt.strftime('%Y%m%d'), dt.strftime('%Y%m%d'))
                if not df_day.empty and 'return' in df_day.columns:
                    ret = df_day['return'].iloc[0]
                    if not np.isnan(ret):
                        daily_ret += ret
                        count += 1
            if count > 0:
                daily_ret /= count
            prev_nav = daily_nav[daily_nav.index < dt].iloc[-1] if len(daily_nav[daily_nav.index < dt]) > 0 else 1.0
            daily_nav[dt] = prev_nav * (1 + daily_ret)

    # 基准净值（沪深300）
    benchmark = get_stock_data("000300", start_date, end_date)
    if not benchmark.empty:
        benchmark_nav = (1 + benchmark['return']).cumprod()
        benchmark_nav = benchmark_nav.reindex(daily_nav.index, method='ffill').fillna(1)
    else:
        benchmark_nav = pd.Series(1.0, index=daily_nav.index)

    # 绩效指标
    daily_nav = daily_nav.fillna(1)
    total_days = len(daily_nav.dropna())
    years = total_days / 252
    total_return = daily_nav.iloc[-1] - 1
    annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
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
    nav, bench, metrics, trades = multi_factor_backtest(START_DATE, END_DATE)
    print("\n绩效报告:")
    for k, v in metrics.items():
        print(f"{k}: {v:.4f}" if isinstance(v, float) else f"{k}: {v}")
    plot_results(nav, bench)
    save_results_to_excel("multi_factor_report.xlsx", metrics, trades, nav, bench)