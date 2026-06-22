# backtest/single_backtest.py
import pandas as pd
import numpy as np
from .metrics import calculate_metrics   # 相对导入，同包
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
    
    if rebalance_freq == 'W':
        df['signal'] = df['signal'].where(df.index.weekday == 4, 0)
    elif rebalance_freq == 'M':
        df['signal'] = df['signal'].where(df.index.is_month_end, 0)
    
    df['return'] = df['close'].pct_change()
    df['position'] = df['position'].fillna(0).astype(int)
    df['strategy_return'] = df['position'].shift(1) * df['return']
    
    trade_cost = commission + slippage
    df['strategy_return'] = df['strategy_return'] - df['signal'].abs() * trade_cost

    if stop_loss_atr_mult is not None and stop_loss_atr_mult > 0:
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close = (df['low'] - df['close'].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        entry_price = 0.0
        for idx in range(len(df)):
            if df['signal'].iloc[idx] == 1:
                entry_price = df['close'].iloc[idx]
                current_atr = atr.iloc[idx]
                if pd.isna(current_atr):
                    current_atr = 0
                stop_price = entry_price - stop_loss_atr_mult * current_atr
            elif df['position'].iloc[idx] == 1 and entry_price > 0:
                if df['close'].iloc[idx] <= stop_price:
                    df.loc[df.index[idx], 'position'] = 0
                    df.loc[df.index[idx], 'signal'] = -2
                    entry_price = 0.0
            elif df['position'].iloc[idx] == 0:
                entry_price = 0.0

    df['strategy_net'] = (1 + df['strategy_return']).cumprod()
    df['benchmark_net'] = (1 + df['return']).cumprod()
    df['strategy_value'] = initial_capital * df['strategy_net']
    df['benchmark_value'] = initial_capital * df['benchmark_net']
    return df

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