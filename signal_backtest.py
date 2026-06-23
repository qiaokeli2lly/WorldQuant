# factors/signal_backtest.py
import pandas as pd
import numpy as np
from data.data_manager import DataManager

def backtest_signals(symbol, signal_type='golden_cross', short_ma=5, long_ma=20,
                     rsi_period=14, rsi_threshold=30, forward_days=[1, 5, 10, 20]):
    dm = DataManager()
    end = pd.Timestamp.now().strftime('%Y%m%d')
    start = (pd.Timestamp.now() - pd.DateOffset(years=4)).strftime('%Y%m%d')
    df = dm.get_stock_data(symbol, start, end)
    if df.empty or len(df) < 500:
        return {"error": "历史数据不足"}

    close = df['close']
    signals = pd.Series(0, index=df.index)

    if signal_type == 'golden_cross':
        ma_s = close.rolling(short_ma).mean()
        ma_l = close.rolling(long_ma).mean()
        signals[(ma_s > ma_l) & (ma_s.shift(1) <= ma_l.shift(1))] = 1
        signal_name = f"金叉(MA{short_ma}上穿MA{long_ma})"
    elif signal_type == 'death_cross':
        ma_s = close.rolling(short_ma).mean()
        ma_l = close.rolling(long_ma).mean()
        signals[(ma_s < ma_l) & (ma_s.shift(1) >= ma_l.shift(1))] = 1
        signal_name = f"死叉(MA{short_ma}下穿MA{long_ma})"
    elif signal_type == 'rsi_oversold':
        rsi = close.rolling(rsi_period).apply(
            lambda x: 100 - (100 / (1 + (x.diff().clip(lower=0).mean() / (-x.diff().clip(upper=0).mean()))))
        )
        signals[rsi < rsi_threshold] = 1
        signal_name = f"RSI超卖(RSI<{rsi_threshold})"
    elif signal_type == 'rsi_overbought':
        rsi = close.rolling(rsi_period).apply(
            lambda x: 100 - (100 / (1 + (x.diff().clip(lower=0).mean() / (-x.diff().clip(upper=0).mean()))))
        )
        signals[rsi > rsi_threshold] = 1
        signal_name = f"RSI超买(RSI>{rsi_threshold})"
    elif signal_type == 'bollinger_lower':
        mid = close.rolling(20).mean()
        std = close.rolling(20).std()
        lower = mid - 2 * std
        signals[close <= lower] = 1
        signal_name = "布林带下轨"
    elif signal_type == 'bollinger_upper':
        mid = close.rolling(20).mean()
        std = close.rolling(20).std()
        upper = mid + 2 * std
        signals[close >= upper] = 1
        signal_name = "布林带上轨"
    else:
        return {"error": f"不支持的信号类型: {signal_type}"}

    signal_dates = signals[signals == 1].index
    total_signals = len(signal_dates)
    if total_signals == 0:
        return {"error": f"历史中没有出现{signal_name}信号"}

    result = {
        "symbol": symbol,
        "signal": signal_name,
        "total_occurrences": total_signals,
        "period": f"{df.index[0].strftime('%Y-%m-%d')} 至 {df.index[-1].strftime('%Y-%m-%d')}",
        "forward_performance": {}
    }

    for days in forward_days:
        returns = []
        for dt in signal_dates:
            try:
                idx = df.index.get_loc(dt)
                if idx + days < len(df):
                    ret = df['close'].iloc[idx + days] / df['close'].iloc[idx] - 1
                    returns.append(ret)
            except:
                continue
        if returns:
            win_rate = sum(1 for r in returns if r > 0) / len(returns)
            avg_ret = np.mean(returns)
            result["forward_performance"][f"{days}日"] = {
                "胜率": round(win_rate, 4),
                "平均收益": round(avg_ret, 4),
                "样本数": len(returns)
            }

    all_returns = []
    max_fwd = max(forward_days)
    for i in range(len(df) - max_fwd):
        ret = df['close'].iloc[i + max_fwd] / df['close'].iloc[i] - 1
        all_returns.append(ret)
    if all_returns:
        random_win = sum(1 for r in all_returns if r > 0) / len(all_returns)
        random_avg = np.mean(all_returns)
        result["random_baseline"] = {
            f"{max_fwd}日胜率": round(random_win, 4),
            f"{max_fwd}日平均收益": round(random_avg, 4)
        }

    return result