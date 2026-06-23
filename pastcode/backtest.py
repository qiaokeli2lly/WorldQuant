# backtest.py
import pandas as pd
import numpy as np
from plot_charts import plot_equity_curve
from strategies.ma_strategy import ma_strategy
from strategies.rsi_strategy import rsi_strategy
from strategies.bollinger_strategy import bollinger_strategy

def generate_signals(df, short_ma=5, long_ma=20):
    df = df.copy()
    ma_short = f'MA{short_ma}'
    ma_long = f'MA{long_ma}'
    if ma_short not in df.columns or ma_long not in df.columns:
        raise ValueError(f"缺少 {ma_short} 或 {ma_long} 列")
    df['position'] = (df[ma_short] > df[ma_long]).astype(int)
    df['signal'] = df['position'].diff()
    return df

def run_backtest(df, commission=0.001, slippage=0.001, initial_capital=100000, rebalance_freq='D',
                 stop_loss_atr_mult=None):
    df = df.copy()
    if 'signal' not in df.columns:
        raise ValueError("缺少 signal 列")
    
    # 根据调仓频率过滤信号
    if rebalance_freq == 'W':
        df['signal'] = df['signal'].where(df.index.weekday == 4, 0)
    elif rebalance_freq == 'M':
        df['signal'] = df['signal'].where(df.index.is_month_end, 0)
    # 其他情况（'D'）保留所有信号
    
    df['return'] = df['close'].pct_change()
    df['position'] = df['position'].fillna(0).astype(int)
    df['strategy_return'] = df['position'].shift(1) * df['return']
    
    # 交易成本
    trade_cost = commission + slippage
    df['strategy_return'] = df['strategy_return'] - df['signal'].abs() * trade_cost

    # 动态止损逻辑
    if stop_loss_atr_mult is not None and stop_loss_atr_mult > 0:
        # 计算 ATR (14日)
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close = (df['low'] - df['close'].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        # 跟踪每笔买入的价格
        entry_price = 0.0
        for idx in range(len(df)):
            if df['signal'].iloc[idx] == 1:   # 买入信号
                entry_price = df['close'].iloc[idx]
                current_atr = atr.iloc[idx]
                if pd.isna(current_atr):
                    current_atr = 0
                stop_price = entry_price - stop_loss_atr_mult * current_atr
            elif df['position'].iloc[idx] == 1 and entry_price > 0:
                if df['close'].iloc[idx] <= stop_price:
                    # 止损平仓
                    df.loc[df.index[idx], 'position'] = 0
                    df.loc[df.index[idx], 'signal'] = -2
                    entry_price = 0.0
            elif df['position'].iloc[idx] == 0:
                entry_price = 0.0

    # 净值计算
    df['strategy_net'] = (1 + df['strategy_return']).cumprod()
    df['benchmark_net'] = (1 + df['return']).cumprod()
    df['strategy_value'] = initial_capital * df['strategy_net']
    df['benchmark_value'] = initial_capital * df['benchmark_net']

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
        elif signal == -2 and buy_date is not None:  # 止损
            sell_date = idx
            sell_price = close
            pct_return = (sell_price - buy_price) / buy_price
            trades.append({
                '买入日期': buy_date.strftime('%Y-%m-%d'),
                '卖出日期': sell_date.strftime('%Y-%m-%d'),
                '买入价': round(buy_price, 2),
                '卖出价': round(sell_price, 2),
                '盈亏(%)': round(pct_return * 100, 2),
                '止损': '是'
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

def multi_strategy_backtest(df, strategies_config, commission=0.001, slippage=0.001, initial_capital=100000, rebalance_freq='D'):
    results = {}
    for cfg in strategies_config:
        name = cfg['name']
        strategy_func = cfg['strategy_func']
        params = cfg['params']
        try:
            df_sig = strategy_func(df.copy(), **params)
            df_bt = run_backtest(df_sig, commission, slippage, initial_capital, rebalance_freq)
            metrics = calculate_metrics(df_bt)
            results[name] = {'df': df_bt, 'metrics': metrics, 'params': params}
        except Exception as e:
            print(f"策略 {name} 回测失败: {e}")
            results[name] = None
    return results

def grid_search_ma(df, short_range, long_range, step=1, commission=0.001, slippage=0.001, initial_capital=100000, rebalance_freq='D'):
    short_vals = list(range(short_range[0], short_range[1]+1, step))
    long_vals = list(range(long_range[0], long_range[1]+1, step))
    sharpe_matrix = np.full((len(short_vals), len(long_vals)), np.nan)
    df_temp = df.copy()
    all_periods = set(short_vals + long_vals)
    for p in all_periods:
        df_temp[f'MA{p}'] = df_temp['close'].rolling(p).mean()
    for i, short in enumerate(short_vals):
        for j, long in enumerate(long_vals):
            if short >= long:
                continue
            try:
                df_sig = ma_strategy(df_temp, short, long)
                df_bt = run_backtest(df_sig, commission, slippage, initial_capital, rebalance_freq)
                metrics = calculate_metrics(df_bt)
                sharpe = metrics.get('夏普比率', np.nan)
                if not np.isnan(sharpe):
                    sharpe_matrix[i, j] = sharpe
            except:
                continue
    return short_vals, long_vals, sharpe_matrix

def full_backtest(df, short_ma=5, long_ma=20, commission=0.001, slippage=0.001, initial_capital=100000, rebalance_freq='D'):
    df = generate_signals(df, short_ma, long_ma)
    df = run_backtest(df, commission, slippage, initial_capital, rebalance_freq)
    metrics = calculate_metrics(df)
    return df, metrics