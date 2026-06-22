# data/us_stock_data.py
import yfinance as yf
import pandas as pd
from datetime import datetime

def get_us_stock_data(symbol, start_date, end_date):
    """
    通过 yfinance 获取美股日线数据，返回统一格式 DataFrame
    symbol: 美股代码，如 'AAPL'
    start_date, end_date: 'YYYYMMDD' 字符串
    """
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date)
        if df.empty:
            print(f"yfinance 未获取到 {symbol} 数据")
            return pd.DataFrame()

        # 统一列名
        df = df.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })
        df.index = pd.to_datetime(df.index)
        df.index.name = 'date'
        df.sort_index(inplace=True)
        df['return'] = df['close'].pct_change()
        return df[['open', 'high', 'low', 'close', 'volume', 'return']]
    except Exception as e:
        print(f"获取美股数据失败: {e}")
        return pd.DataFrame()