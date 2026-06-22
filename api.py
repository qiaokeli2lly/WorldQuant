# agent/api.py
from fastapi import FastAPI
from pydantic import BaseModel
from agent.tools import (
    TOOLS,
    StockDataInput,
    FundamentalInput,
    SmartAnalysisInput,
    ProfileInput,
    FactorValidationInput,
    SignalBacktestInput,
    RiskAnalysisInput,
    IndustryCompareInput,
)
from agent.agent import run_agent
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import time
import math
import pandas as pd
from utils.stock_pool import get_predefined_pool
from intelligence.data_sources import get_all_news_concurrent
from intelligence.local_db import init_db, insert_articles

app = FastAPI(title="MiniQuant Agent API")


# -------------------- 数据清洗工具 --------------------
def sanitize_for_json(obj):
    """递归清理 NaN、NaT、Timestamp 等无法被 JSON 序列化的类型"""
    if isinstance(obj, float) and math.isnan(obj):
        return None
    elif isinstance(obj, pd.Timestamp):
        return str(obj)
    elif isinstance(obj, pd.Series):
        return sanitize_for_json(obj.to_dict())
    elif isinstance(obj, pd.DataFrame):
        return sanitize_for_json(obj.to_dict(orient='records'))
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(i) for i in obj]
    elif obj is pd.NaT:
        return None
    return obj


# -------------------- 定时任务 --------------------
def fetch_news_for_symbol(symbol):
    try:
        df = get_all_news_concurrent(symbol, limit_per_source=15, max_total=30)
        if not df.empty:
            articles = []
            for _, row in df.iterrows():
                articles.append(
                    {
                        "symbol": symbol,
                        "title": row["title"],
                        "summary": row.get("content", "")[:300],
                        "source": row["source"],
                        "url": row.get("url", ""),
                        "pub_date": row.get("pub_date", ""),
                    }
                )
            count = insert_articles(articles)
            print(f"[定时任务] {symbol} 新增 {count} 条新闻")
            return count
    except Exception as e:
        print(f"[定时任务] {symbol} 抓取失败: {e}")
    return 0


def daily_news_job():
    print("[定时任务] 开始每日新闻抓取...")
    init_db()
    stocks = get_predefined_pool("demo") + get_predefined_pool("us_top20")
    total = 0
    for i, sym in enumerate(stocks):
        count = fetch_news_for_symbol(sym)
        total += count
        if i < len(stocks) - 1:
            time.sleep(1.5)
    print(f"[定时任务] 完成，共新增 {total} 条新闻")


scheduler = BackgroundScheduler()
scheduler.add_job(
    daily_news_job, "cron", hour=9, minute=30, id="daily_news", misfire_grace_time=30
)
scheduler.start()
print("新闻定时任务已启动（每日 9:30 执行，错过自动补执行）")
atexit.register(lambda: scheduler.shutdown())


# -------------------- 请求模型 --------------------
class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: dict


class ChatRequest(BaseModel):
    query: str


# -------------------- 工具端点（统一清洗返回值）--------------------
@app.post("/tools/call")
def call_tool(req: ToolCallRequest):
    if req.tool_name not in TOOLS:
        return {"error": f"未知工具: {req.tool_name}"}
    tool = TOOLS[req.tool_name]
    try:
        result = tool["function"](**req.arguments)
        result = sanitize_for_json(result)
        return {"data": result}
    except Exception as e:
        return {"error": str(e)}


@app.post("/tools/get_stock_data")
def api_get_stock_data(req: StockDataInput):
    result = TOOLS["get_stock_data"]["function"](req.symbol, req.start_date, req.end_date)
    result = sanitize_for_json(result)
    return {"data": result}


@app.post("/tools/get_fundamental")
def api_get_fundamental(req: FundamentalInput):
    result = TOOLS["get_fundamental"]["function"](req.symbol)
    result = sanitize_for_json(result)
    return {"data": result}


@app.post("/tools/smart_analysis")
def api_smart_analysis(req: SmartAnalysisInput):
    result = TOOLS["smart_analysis"]["function"](req.symbol, req.stock_name, req.model)
    result = sanitize_for_json(result)
    return {"data": result}


@app.post("/tools/get_stock_profile")
def api_get_stock_profile(req: ProfileInput):
    result = TOOLS["get_stock_profile"]["function"](req.symbol, req.date)
    result = sanitize_for_json(result)
    return {"data": result}


@app.post("/tools/factor_validation")
def api_factor_validation(req: FactorValidationInput):
    result = TOOLS["factor_validation"]["function"](req.symbol, req.factor, req.lookback)
    result = sanitize_for_json(result)
    return {"data": result}


@app.post("/tools/signal_backtest")
def api_signal_backtest(req: SignalBacktestInput):
    result = TOOLS["signal_backtest"]["function"](
        req.symbol, req.signal_type, req.short_ma, req.long_ma
    )
    result = sanitize_for_json(result)
    return {"data": result}


@app.post("/tools/risk_analysis")
def api_risk_analysis(req: RiskAnalysisInput):
    result = TOOLS["risk_analysis"]["function"](req.symbol)
    result = sanitize_for_json(result)
    return {"data": result}


@app.post("/tools/industry_compare")
def api_industry_compare(req: IndustryCompareInput):
    result = TOOLS["industry_compare"]["function"](req.symbol)
    result = sanitize_for_json(result)
    return {"data": result}


@app.post("/chat")
def chat(req: ChatRequest):
    reply = run_agent(req.query)
    return {"reply": reply}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)