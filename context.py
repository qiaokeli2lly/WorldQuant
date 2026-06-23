# intelligence/context.py
from data.stock_data import get_stock_data
from factors.price_factors import calc_momentum, calc_volatility
import pandas as pd
from datetime import datetime, timedelta

# 简单行业背景字典（可扩展）
INDUSTRY_BG = {
    '白酒': '白酒行业品牌壁垒高，消费升级趋势下高端需求稳定，需关注政策影响。',
    '新能源': '新能源受政策驱动，技术迭代快，补贴退坡和产能过剩是主要风险。',
    '银行': '银行业盈利稳定、股息率高，但受利率与经济周期影响大。',
}
DEFAULT_BG = '行业竞争格局稳定，需关注宏观经济变化。'

def get_industry_bg(symbol: str) -> str:
    # 实际项目可从 Tushare 获取行业分类，这里简化处理
    return DEFAULT_BG

def get_quant_snapshot(symbol: str, date: str = None) -> str:
    """返回一句话量化快照：动量、波动率、均线位置"""
    if not date:
        date = datetime.now().strftime('%Y%m%d')
    end = pd.to_datetime(date)
    start = end - timedelta(days=120)
    df = get_stock_data(symbol, start.strftime('%Y%m%d'), end.strftime('%Y%m%d'))
    if df.empty or len(df) < 30:
        return "量化数据不足"

    close = df['close']
    mom_20 = calc_momentum(close, 20)       # 20日动量
    mom_60 = calc_momentum(close, 60)       # 60日动量
    vol_20 = calc_volatility(close, 20)     # 20日波动率
    ma20 = close.rolling(20).mean().iloc[-1]
    latest = close.iloc[-1]
    ma20_pct = (latest / ma20 - 1) * 100

    mom_desc = "偏强" if mom_20 > 0.05 else ("偏弱" if mom_20 < -0.05 else "中性")
    vol_desc = "高" if vol_20 > 0.02 else ("低" if vol_20 < 0.01 else "中等")

    snapshot = (f"20日动量{mom_desc}({mom_20:.3f})，60日动量{mom_60:.3f}，"
                f"波动率{vol_desc}({vol_20:.3f})，距20日均线{ma20_pct:+.1f}%")
    return snapshot