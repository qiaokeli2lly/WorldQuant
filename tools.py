# agent/tools.py
import pandas as pd
from pydantic import BaseModel, Field
from data.stock_data import get_stock_data
from data.fundamental import get_fundamental_single
from intelligence.analyzer import analyze_stock
from features.stock_profile import get_stock_profile
from factors.factor_validation import validate_factor
from factors.signal_backtest import backtest_signals
from factors.risk_analysis import risk_analysis
from factors.industry_compare import industry_compare

def is_us_stock(symbol: str) -> bool:
    return symbol.isalpha() and not symbol.isdigit()

# ========== 工具1：行情 ==========
class StockDataInput(BaseModel):
    symbol: str = Field(description="股票代码")
    start_date: str = Field(description="开始日期，YYYYMMDD")
    end_date: str = Field(description="结束日期，YYYYMMDD")

def get_stock_data_func(symbol: str, start_date: str, end_date: str) -> dict:
    if is_us_stock(symbol):
        from data.us_stock_data import get_us_stock_data
        df = get_us_stock_data(symbol, start_date, end_date)
    else:
        df = get_stock_data(symbol, start_date, end_date)
    if df.empty:
        return {"error": "无数据"}
    result_df = df.tail(30).reset_index(names='date')
    result_df['date'] = pd.to_datetime(result_df['date']).dt.strftime('%Y-%m-%d')
    return {
        "data": result_df.to_dict(orient='records'),
        "summary": f"最新价{df['close'].iloc[-1]:.2f}"
    }

# ========== 工具2：基本面 ==========
class FundamentalInput(BaseModel):
    symbol: str = Field(description="股票代码")

def get_fundamental_func(symbol: str) -> dict:
    if is_us_stock(symbol):
        return {"error": "仅支持A股"}
    data = get_fundamental_single(symbol)
    return data if data else {"error": "数据获取失败"}

# ========== 工具3：智能分析 ==========
class SmartAnalysisInput(BaseModel):
    symbol: str = Field(description="股票代码")
    stock_name: str = Field(default="")
    model: str = Field(default="deepseek")

def smart_analysis_func(symbol, stock_name="", model="deepseek"):
    result = analyze_stock(symbol, stock_name, model)
    if 'error' in result:
        return {"error": result['error']}
    return result

# ========== 工具4：特征画像 ==========
class ProfileInput(BaseModel):
    symbol: str = Field(description="股票代码")
    date: str = Field(default=None, description="分析日期，格式YYYYMMDD，如20250622。不传则默认为今天")

def get_profile_func(symbol, date=None):
    return get_stock_profile(symbol, date)

# ========== 工具5：因子检验 ==========
class FactorValidationInput(BaseModel):
    symbol: str
    factor: str = Field(default="momentum")
    lookback: int = Field(default=20)

def factor_validation_func(symbol, factor="momentum", lookback=20):
    return validate_factor(symbol, factor, lookback)

# ========== 工具6：信号统计 ==========
class SignalBacktestInput(BaseModel):
    symbol: str
    signal_type: str = Field(default="golden_cross", 
                            description="golden_cross|death_cross|rsi_oversold|rsi_overbought|bollinger_lower|bollinger_upper")
    short_ma: int = 5
    long_ma: int = 20

def signal_backtest_func(symbol, signal_type="golden_cross", short_ma=5, long_ma=20):
    return backtest_signals(symbol, signal_type, short_ma, long_ma)

# ========== 工具7：风险分析 ==========
class RiskAnalysisInput(BaseModel):
    symbol: str

def risk_analysis_func(symbol):
    return risk_analysis(symbol)

# ========== 工具8：行业对比 ==========
class IndustryCompareInput(BaseModel):
    symbol: str

def industry_compare_func(symbol):
    return industry_compare(symbol)

# ========== 注册表 ==========
TOOLS = {
    "get_stock_data": {
        "description": "获取股票日线行情",
        "parameters": StockDataInput.schema(),
        "function": get_stock_data_func
    },
    "get_fundamental": {
        "description": "获取基本面",
        "parameters": FundamentalInput.schema(),
        "function": get_fundamental_func
    },
    "smart_analysis": {
        "description": "智能分析",
        "parameters": SmartAnalysisInput.schema(),
        "function": smart_analysis_func
    },
    "get_stock_profile": {
        "description": "六维特征画像",
        "parameters": ProfileInput.schema(),
        "function": get_profile_func
    },
    "factor_validation": {
        "description": "因子有效性检验(IC值、分层回测)",
        "parameters": FactorValidationInput.schema(),
        "function": factor_validation_func
    },
    "signal_backtest": {
        "description": "信号胜率统计(金叉/死叉/RSI/布林带)",
        "parameters": SignalBacktestInput.schema(),
        "function": signal_backtest_func
    },
    "risk_analysis": {
        "description": "风险分析(VaR/CVaR/波动率锥/回撤)",
        "parameters": RiskAnalysisInput.schema(),
        "function": risk_analysis_func
    },
    "industry_compare": {
        "description": "同行业对比(估值/因子排名)",
        "parameters": IndustryCompareInput.schema(),
        "function": industry_compare_func
    }
}