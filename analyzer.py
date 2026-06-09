# intelligence/analyzer.py
import json
from datetime import datetime, timedelta
from .data_sources import get_news, get_announcements, get_moneyflow, get_concept
from .llm_gateway import LLMGateway
from .prompts import SYSTEM_PROMPT, build_user_prompt

MODEL_FALLBACK_CHAIN = {
    'deepseek': ['deepseek', 'qwen', 'ollama'],
    'qwen': ['qwen', 'ollama'],
    'ollama': ['ollama']
}

def _fetch_news_and_announcements(symbol):
    """
    智能获取新闻和公告：先拉取近30天数据，若条数少于3条则扩大到365天。
    返回 (news_df, announcements_df, actual_start_date_str)
    """
    end_date = datetime.now().strftime('%Y%m%d')
    # 第一阶段：近30天
    start_date_30 = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
    news_df = get_news(symbol, start_date_30, end_date)
    announcements_df = get_announcements(symbol, start_date_30, end_date)

    # 判断是否需要扩大范围（新闻+公告总条数 < 3）
    total_items = (len(news_df) if not news_df.empty else 0) + (len(announcements_df) if not announcements_df.empty else 0)
    if total_items < 3:
        start_date_365 = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        news_df = get_news(symbol, start_date_365, end_date)
        announcements_df = get_announcements(symbol, start_date_365, end_date)
        return news_df, announcements_df, start_date_365
    return news_df, announcements_df, start_date_30


def analyze_stock(symbol, stock_name="", model='deepseek'):
    end_date = datetime.now().strftime('%Y%m%d')

    # ----- 获取新闻和公告（智能扩大时间范围）-----
    news_df, announcements_df, actual_start = _fetch_news_and_announcements(symbol)

    # ----- 获取其他数据 -----
    concepts = get_concept(symbol)
    moneyflow_df = get_moneyflow(symbol, actual_start, end_date)

    news_text = "\n".join(news_df['title'].tolist()) if not news_df.empty else "无"
    announcements_text = "\n".join(announcements_df['title'].tolist()) if not announcements_df.empty else "无"
    moneyflow_text = "无数据"
    if not moneyflow_df.empty and 'buy_elg_amount' in moneyflow_df.columns:
        total_buy = moneyflow_df['buy_elg_amount'].sum()
        moneyflow_text = f"近一年主力净买入(超大单): {total_buy:.2f}万元"  # 若范围扩大，说明

    from data.fundamental import get_fundamental_single
    fund = get_fundamental_single(symbol)
    fundamentals_text = str(fund) if fund else "无"

    raw_data = {
        "fundamentals": fundamentals_text,
        "news_titles": news_text,
        "announcements_titles": announcements_text,
        "concepts": concepts,
        "moneyflow": moneyflow_text,
        "data_period": f"数据获取范围：{actual_start} 至 {end_date}"
    }

    user_prompt = build_user_prompt(stock_name or symbol, fundamentals_text,
                                    news_text, announcements_text, concepts, moneyflow_text)

    models_to_try = MODEL_FALLBACK_CHAIN.get(model, [model])
    last_error = None

    for m in models_to_try:
        try:
            gateway = LLMGateway(m)
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
            result_text = gateway.chat(messages)
            original_text = result_text

            # 尝试解析 JSON
            analysis = None
            try:
                analysis = json.loads(result_text)
            except json.JSONDecodeError:
                start = result_text.find('{')
                end = result_text.rfind('}')
                if start != -1 and end != -1 and end > start:
                    try:
                        analysis = json.loads(result_text[start:end+1])
                    except:
                        pass

            if analysis is None:
                return {
                    "error": f"模型返回格式不正确，无法解析。原始输出: {original_text[:300]}",
                    "raw_output": original_text,
                    "raw_data": raw_data
                }

            analysis['used_model'] = m
            if m != model:
                analysis['fallback'] = True
            analysis['raw_data'] = raw_data
            return analysis

        except Exception as e:
            last_error = e
            continue

    return {
        "error": f"所有模型调用失败。最后错误: {last_error}",
        "raw_data": raw_data
    }