# data/us_stock_data.py
import finnhub
import pandas as pd
import os
import time
from datetime import datetime

def get_us_stock_data(symbol, start_date, end_date):
    """
    获取美股日线数据，返回统一 DataFrame（兼容现有系统）
    symbol: 美股代码，如 'AAPL'
    start_date, end_date: 'YYYYMMDD' 字符串
    """
    api_key = os.getenv('FINNHUB_API_KEY', '')
    if not api_key:
        raise ValueError("FINNHUB_API_KEY 未设置，无法获取美股数据")

    client = finnhub.Client(api_key=api_key)
    # Finnhub 免费版限制 60 次/分钟，加一点延时
    time.sleep(0.5)

    # 转换日期为 Unix 时间戳（Finnhub 要求）
    start_ts = int(datetime.strptime(start_date, '%Y%m%d').timestamp())
    end_ts = int(datetime.strptime(end_date, '%Y%m%d').timestamp())

    try:
        res = client.stock_candles(symbol, 'D', start_ts, end_ts)
        if res['s'] != 'ok':
            print(f"Finnhub 返回错误: {res}")
            return pd.DataFrame()

        df = pd.DataFrame({
            'date': pd.to_datetime(res['t'], unit='s'),
            'open': res['o'],
            'high': res['h'],
            'low': res['l'],
            'close': res['c'],
            'volume': res['v']
        })
        df.set_index('date', inplace=True)
        df.sort_index(inplace=True)
        df['return'] = df['close'].pct_change()
        return df
    except Exception as e:
        print(f"获取美股数据失败: {e}")
        return pd.DataFrame()