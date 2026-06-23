# factors/sentiment_factor.py
from intelligence.local_db import get_sentiment, save_sentiment
from intelligence.analyzer import analyze_stock_at_date

def build_sentiment_cache(stock_list, rebalance_dates):
    """
    为回测区间内的所有股票和调仓日生成情感因子缓存。
    stock_list: 股票代码列表
    rebalance_dates: 调仓日期列表 (pd.Timestamp)
    """
    for date in rebalance_dates:
        date_str = date.strftime('%Y%m%d')
        for sym in stock_list:
            existing = get_sentiment(sym, date_str)
            if existing is not None:
                continue  # 已有缓存
            score = analyze_stock_at_date(sym, date_str)
            save_sentiment(sym, date_str, score)
            print(f"情感缓存 {sym} {date_str}: {score:.2f}")

def get_sentiment_factor(symbol, date):
    """获取情绪因子值，缺失返回 0.5"""
    s = get_sentiment(symbol, date)
    return s if s is not None else 0.5  