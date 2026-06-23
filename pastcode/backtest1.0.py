import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from plot_charts import plot_equity_curve   # 新增导入

def generate_signals(df, short_ma=5, long_ma=20):
    """
    根据双均线策略生成交易信号
    - short_ma: 短期均线周期
    - long_ma: 长期均线周期
    返回添加了 position (持仓) 和 signal (买卖信号) 列的 DataFrame
    """
    df = df.copy()
    ma_short = f'MA{short_ma}'
    ma_long = f'MA{long_ma}'
    if ma_short not in df.columns or ma_long not in df.columns:
        raise ValueError(f"DataFrame 中缺少 {ma_short} 或 {ma_long} 列，请先计算均线。")
    
    df['position'] = (df[ma_short] > df[ma_long]).astype(int)
    df['signal'] = df['position'].diff()
    return df

def run_backtest(df, commission=0.001, slippage=0.001):
    """
    执行回测，计算策略净值、基准净值等
    - commission: 单边手续费率
    - slippage: 滑点
    """
    df = df.copy()
    if 'signal' not in df.columns:
        df = generate_signals(df)
    
    df['return'] = df['close'].pct_change()
    df['strategy_return'] = df['position'].shift(1) * df['return']
    
    trade_cost = (commission + slippage)
    df['strategy_return'] = df['strategy_return'] - df['signal'].abs() * trade_cost
    
    df['strategy_net'] = (1 + df['strategy_return']).cumprod()
    df['benchmark_net'] = (1 + df['return']).cumprod()
    return df

def calculate_metrics(df, risk_free_rate=0.03):
    """
    计算核心绩效指标
    """
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
    
    trades = df[df['signal'].notna() & (df['signal'] != 0)]
    metrics = {
        '总收益率（策略）': total_return_strategy,
        '年化收益率（策略）': annual_return,
        '总收益率（基准）': total_return_benchmark,
        '年化收益率（基准）': annual_return_benchmark,
        '最大回撤': max_drawdown,
        '夏普比率': sharpe_ratio,
        '总交易日数': total_days,
        '交易次数': len(trades)
    }
    return metrics

def print_metrics(metrics):
    """格式化打印绩效指标"""
    print("\n========== 回测绩效报告 ==========")
    for key, value in metrics.items():
        if isinstance(value, float):
            if '收益率' in key or '回撤' in key:
                print(f"{key}: {value:.2%}")
            elif '夏普' in key:
                print(f"{key}: {value:.4f}")
            else:
                print(f"{key}: {value:.4f}")
        else:
            print(f"{key}: {value}")
    print("===================================\n")

def full_backtest(df, short_ma=5, long_ma=20, commission=0.001, slippage=0.001):
    """
    一站式回测函数：生成信号 → 运行回测 → 计算绩效
    """
    df = generate_signals(df, short_ma, long_ma)
    df = run_backtest(df, commission, slippage)
    metrics = calculate_metrics(df)
    return df, metrics

if __name__ == "__main__":
    from data_utils import get_stock_data
    from indicators import compute_all_indicators
    
    # 获取数据并计算技术指标
    df = get_stock_data("600519", "20200101", "20241231")
    df = compute_all_indicators(df)
    
    # 运行回测
    df_result, metrics = full_backtest(df, short_ma=5, long_ma=20, commission=0.001, slippage=0.001)
    
    # 打印绩效
    print_metrics(metrics)
    
    # 显示最后10行数据
    print("\n最后10行数据预览（信号、持仓、净值）：")
    print(df_result[['close', 'MA5', 'MA20', 'position', 'signal', 'strategy_net', 'benchmark_net']].tail(10))
    
    # ===== 新增可视化：绘制资金曲线 =====
    fig = plot_equity_curve(df_result, benchmark_col='benchmark_net', strategy_col='strategy_net')
    plt.show()