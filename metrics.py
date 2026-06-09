# backtest/metrics.py
import numpy as np

def calculate_metrics(df, risk_free_rate=0.03):
    if df.empty or 'strategy_net' not in df.columns:
        return {}
    strategy_net = df['strategy_net']
    benchmark_net = df['benchmark_net']
    total_days = len(df)
    years = total_days / 252
    total_return_strategy = strategy_net.iloc[-1] - 1
    annual_return = (1 + total_return_strategy) ** (1 / years) - 1 if years > 0 else 0
    total_return_benchmark = benchmark_net.iloc[-1] - 1
    annual_return_benchmark = (1 + total_return_benchmark) ** (1 / years) - 1 if years > 0 else 0
    cumulative_max = strategy_net.cummax()
    drawdown = (strategy_net - cumulative_max) / cumulative_max
    max_drawdown = drawdown.min()
    daily_returns = df['strategy_return'].dropna()
    if len(daily_returns) > 0 and daily_returns.std() != 0:
        sharpe_ratio = (annual_return - risk_free_rate) / (daily_returns.std() * np.sqrt(252))
    else:
        sharpe_ratio = np.nan
    if 'signal' in df.columns:
        trades = df[df['signal'].notna() & (df['signal'] != 0)]
        trade_cnt = len(trades)
    else:
        trade_cnt = 0
    metrics = {
        '年化收益率（策略）': annual_return,
        '累计收益率（策略）': total_return_strategy,
        '年化收益率（基准）': annual_return_benchmark,
        '累计收益率（基准）': total_return_benchmark,
        '最大回撤': max_drawdown,
        '夏普比率': sharpe_ratio,
        '总交易日数': total_days,
        '交易次数': trade_cnt,
        '最终资产(元)': df['strategy_value'].iloc[-1] if 'strategy_value' in df.columns else strategy_net.iloc[-1] * 100000,
        '最终基准资产(元)': df['benchmark_value'].iloc[-1] if 'benchmark_value' in df.columns else benchmark_net.iloc[-1] * 100000
    }
    return metrics

def calc_outperform_stats(df):
    excess = df['strategy_return'] - df['return']
    win_days = (excess > 0).sum()
    total_days = len(excess.dropna())
    win_rate = win_days / total_days if total_days > 0 else 0
    total_excess = df['strategy_net'].iloc[-1] - df['benchmark_net'].iloc[-1]
    avg_excess = excess.mean()
    return {
        '跑赢天数占比': win_rate,
        '累计超额收益(净值)': total_excess,
        '平均日超额收益率': avg_excess
    }