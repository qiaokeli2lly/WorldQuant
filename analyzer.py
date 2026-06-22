import json
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
from difflib import SequenceMatcher

from .data_sources import get_all_news_concurrent, get_moneyflow, get_concept
from .context import get_quant_snapshot, get_industry_bg
from .llm_gateway import LLMGateway
from .prompts import SYSTEM_PROMPT_ENHANCED, build_user_prompt_enhanced
from data.fundamental import get_fundamental_single

# ---------- Pydantic 模型 ----------
class LogicItem(BaseModel):
    event: str
    impact: str
    reason: str

class AnalysisOutput(BaseModel):
    trend: str
    confidence: float
    score: float
    logic_chain: List[LogicItem]
    key_risks: List[str]

# ---------- 模型降级链 ----------
MODEL_FALLBACK_CHAIN = {
    'deepseek': ['deepseek', 'qwen', 'ollama'],
    'qwen': ['qwen', 'ollama'],
    'ollama': ['ollama']
}

# ---------- 简单去重（标题相似度 > 0.8 视为重复）----------
def deduplicate_news(news_df):
    if news_df.empty:
        return news_df
    titles = news_df['title'].tolist()
    keep = []
    for i, row in news_df.iterrows():
        dup = False
        for j in keep:
            if SequenceMatcher(None, titles[i], titles[news_df.index[j]]).ratio() > 0.8:
                dup = True
                break
        if not dup:
            keep.append(i)
    return news_df.loc[keep]

# ---------- 主分析函数 ----------
def analyze_stock(symbol, stock_name="", model='deepseek', manual_news=""):
    # 1. 量化上下文
    quant_snap = get_quant_snapshot(symbol)
    industry = get_industry_bg(symbol)

    # 2. 多源新闻 + 去重
    news_df = get_all_news_concurrent(symbol, limit_per_source=10, max_total=30)
    news_df = deduplicate_news(news_df)

    # 3. 整理文本
    if not news_df.empty:
        news_text = "\n".join([f"[{row['source']}] {row['title']} {row.get('content','')[:100]}"
                               for _, row in news_df.iterrows()])
    else:
        news_text = "无"
    if manual_news.strip():
        news_text += "\n【手动补充】\n" + manual_news

    # 4. 基本面
    fund = get_fundamental_single(symbol)
    fundamentals_text = str(fund) if fund else "无"

    # 5. 构建 prompt
    system_prompt = SYSTEM_PROMPT_ENHANCED.format(
        quant_snapshot=quant_snap,
        industry_bg=industry
    )
    user_prompt = build_user_prompt_enhanced(news_text, stock_name or symbol, fundamentals_text)

    # 6. 调用模型 + 降级
    models_to_try = MODEL_FALLBACK_CHAIN.get(model, [model])
    last_error = None
    raw_data = {
        'fundamentals': fundamentals_text,
        'news_df': news_df,
        'news_count': len(news_df),
        'quant_snapshot': quant_snap,
        'industry_bg': industry,
        'concepts': get_concept(symbol),
        'moneyflow': _get_moneyflow_text(symbol)
    }

    for m in models_to_try:
        try:
            gateway = LLMGateway(m)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            result_text = gateway.chat(messages)

            # 7. 清理并解析 JSON
            cleaned = result_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

            # 提取第一个 JSON 对象
            start = cleaned.find('{')
            end = cleaned.rfind('}') + 1
            if start != -1 and end > start:
                cleaned = cleaned[start:end]

            analysis_dict = json.loads(cleaned)

            # 8. Pydantic 校验
            analysis = AnalysisOutput(**analysis_dict)

            # 9. 构造返回结果
            result = analysis.dict()
            result['used_model'] = m
            if m != model:
                result['fallback'] = True
            result['raw_data'] = raw_data
            return result

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            last_error = e
            continue
        except Exception as e:
            last_error = e
            continue

    # 所有模型失败
    return {
        "error": f"所有模型调用失败。最后错误: {last_error}",
        "raw_data": raw_data
    }
    # 放在 analyze_stock 函数附近

def analyze_stock_at_date(symbol, date):
    """
    使用本地数据库中 date 之前的历史新闻，调用 DeepSeek 返回情感得分（0~1）。
    若无新闻或模型失败，返回 0.5（中性）。
    """
    from intelligence.local_db import query_articles
    from intelligence.llm_gateway import LLMGateway
    import json

    # 获取该日期之前的新闻（最多50条）
    news_df = query_articles(symbol, limit=50)
    if news_df is None or news_df.empty:
        return 0.5

    # 只保留日期早于分析日的新闻
    news_df['pub_date'] = pd.to_datetime(news_df['pub_date'])  # 假设有 pub_date 列
    news_df = news_df[news_df['pub_date'] < pd.to_datetime(date)]
    if news_df.empty:
        return 0.5

    # 构建简单 prompt
    titles = "；".join(news_df['title'].tolist()[:20])
    prompt = f"""以下是关于股票 {symbol} 在 {date} 之前的历史新闻标题：
{titles}

请根据这些新闻判断该股票在 {date} 当天的情绪倾向，输出一个 0 到 1 之间的数字，0 表示极度悲观，1 表示极度乐观，0.5 表示中性。只输出数字，不要任何其他文字。"""

    try:
        gateway = LLMGateway('deepseek')
        result = gateway.chat([{"role": "user", "content": prompt}], temperature=0.1, max_tokens=10)
        score = float(result.strip())
        return max(0.0, min(1.0, score))  # 限制在 0~1
    except:
        return 0.5

def _get_moneyflow_text(symbol):
    try:
        df = get_moneyflow(symbol,
                           (datetime.now() - timedelta(days=30)).strftime('%Y%m%d'),
                           datetime.now().strftime('%Y%m%d'))
        if not df.empty and 'buy_elg_amount' in df.columns:
            return f"近一月主力净买入(超大单): {df['buy_elg_amount'].sum():.2f}万元"
    except:
        pass
    return "无数据"