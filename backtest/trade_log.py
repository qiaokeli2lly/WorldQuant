# backtest/trade_log.py
import pandas as pd
import numpy as np

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
        elif signal == -2 and buy_date is not None:
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