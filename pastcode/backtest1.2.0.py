import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from plot_charts import plot_equity_curve

def generate_signals(df, short_ma=5, long_ma=20):
    df = df.copy()
    ma_short = f'MA{short_ma}'
    ma_long = f'MA{long_ma}'
    if ma_short not in df.columns or ma_long not in df.columns:
        raise ValueError(f"缺少 {ma_short} 或 {ma_long} 列")
    df['position'] = (df[ma_short] > df[ma_long]).astype(int)
    df['signal'] = df['position'].diff()
    return df

def run_backtest(df, commission=0.001, slippage=0.001):
    df = df.copy()
    if 'signal' not in df.columns:
        df = generate_signals(df)
    df['return'] = df['close'].pct_change()
    df['strategy_return'] = df['position'].shift(1) * df['return']
    trade_cost = commission + slippage
    df['strategy_return'] = df['strategy_return'] - df['signal'].abs() * trade_cost
    df['strategy_net'] = (1 + df['strategy_return']).cumprod()
    df['benchmark_net'] = (1 + df['return']).cumprod()
    return df

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
    print("\n========== 回测绩效报告 ==========")
    for k, v in metrics.items():
        if isinstance(v, float):
            if '收益率' in k or '回撤' in k:
                print(f"{k}: {v:.2%}")
            elif '夏普' in k:
                print(f"{k}: {v:.4f}")
            else:
                print(f"{k}: {v:.4f}")
        else:
            print(f"{k}: {v}")
    print("===================================\n")

def get_trade_log(df):
    trades = []
    buy_date = None
    buy_price = None
    for idx, row in df.iterrows():
        signal = row['signal']
        close = row['close']
        if signal == 1:
            buy_date = idx
            buy_price = close
        elif signal == -1 and buy_date is not None:
            sell_date = idx
            sell_price = close
            pct_return = (sell_price - buy_price) / buy_price
            trades.append({
                '买入日期': buy_date.strftime('%Y-%m-%d'),
                '卖出日期': sell_date.strftime('%Y-%m-%d'),
                '买入价': round(buy_price, 2),
                '卖出价': round(sell_price, 2),
                '盈亏(%)': round(pct_return * 100, 2)
            })
            buy_date = None
    if not trades:
        return pd.DataFrame(), {}
    trade_df = pd.DataFrame(trades)
    win = trade_df[trade_df['盈亏(%)'] > 0]
    loss = trade_df[trade_df['盈亏(%)'] < 0]
    total = len(trade_df)
    win_rate = len(win) / total if total > 0 else 0
    avg_win = win['盈亏(%)'].mean() if len(win) > 0 else 0
    avg_loss = loss['盈亏(%)'].mean() if len(loss) > 0 else 0
    profit_factor = abs(win['盈亏(%)'].sum() / loss['盈亏(%)'].sum()) if len(loss) > 0 and loss['盈亏(%)'].sum() != 0 else np.nan
    stats = {
        '交易次数': total,
        '胜率': f"{win_rate*100:.2f}%",
        '平均盈利(%)': round(avg_win, 2),
        '平均亏损(%)': round(avg_loss, 2),
        '盈亏比': round(profit_factor, 2) if not np.isnan(profit_factor) else 'N/A'
    }
    return trade_df, stats

def print_trade_summary(trade_df, stats):
    print("\n========== 交易明细 ==========")
    if trade_df.empty:
        print("无交易记录")
        return
    print(trade_df.to_string(index=False))
    print("\n========== 交易统计 ==========")
    for k, v in stats.items():
        print(f"{k}: {v}")
    print("==============================\n")

def save_results_to_excel(filepath, metrics, trade_df, df_result):
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        metrics_df = pd.DataFrame(list(metrics.items()), columns=['指标', '数值'])
        # 格式化百分比
        metrics_df['数值'] = metrics_df.apply(
            lambda row: f"{row['数值']:.2%}" if isinstance(row['数值'], float) and ('收益率' in row['指标'] or '回撤' in row['指标'])
            else (f"{row['数值']:.4f}" if isinstance(row['数值'], float) and '夏普' in row['指标']
            else row['数值']), axis=1
        )
        metrics_df.to_excel(writer, sheet_name='绩效指标', index=False)
        if trade_df is not None and not trade_df.empty:
            trade_df.to_excel(writer, sheet_name='交易明细', index=False)
        if df_result is not None and not df_result.empty:
            cols = ['close', 'MA5', 'MA20', 'position', 'signal', 'strategy_net', 'benchmark_net']
            available = [c for c in cols if c in df_result.columns]
            df_result[available].to_excel(writer, sheet_name='净值数据', index=True)
    print(f"回测报告已保存至: {filepath}")

def full_backtest(df, short_ma=5, long_ma=20, commission=0.001, slippage=0.001):
    df = generate_signals(df, short_ma, long_ma)
    df = run_backtest(df, commission, slippage)
    metrics = calculate_metrics(df)
    return df, metrics


if __name__ == "__main__":
    from data_utils import get_stock_data
    from indicators import compute_all_indicators

    symbol = "600519"
    start = "20220101"
    end = "20241231"

    df = get_stock_data(symbol, start, end)
    df = compute_all_indicators(df)
    df_result, metrics = full_backtest(df, short_ma=5, long_ma=20, commission=0.001, slippage=0.001)

    print_metrics(metrics)
    trade_log, trade_stats = get_trade_log(df_result)
    print_trade_summary(trade_log, trade_stats)

    # 保存到 Excel（覆盖写入）
    save_results_to_excel("backtest_report.xlsx", metrics, trade_log, df_result)

    # 绘制资金曲线
    fig = plot_equity_curve(df_result, benchmark_col='benchmark_net', strategy_col='strategy_net')
    plt.show()