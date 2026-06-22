# agent/agent.py
import json
import os
from openai import OpenAI
from agent.tools import TOOLS

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

SYSTEM_PROMPT = """你是一个专业的量化投研助手。你能调用以下工具获取实时数据：
- get_stock_data：行情数据
- get_fundamental：基本面数据
- get_stock_profile：六维特征画像（趋势、波动、量价、技术、相对强弱、基本面）
- factor_validation：因子有效性检验（IC值、分层回测、自相关）
- signal_backtest：信号胜率统计（金叉、死叉、RSI超买超卖、布林带上轨下轨）
- risk_analysis：风险分析（VaR、CVaR、波动率锥、最大回撤及恢复时间）
- industry_compare：同行业对比（估值分位、因子排名）

你的分析必须基于工具返回的客观数据，结合金融知识库中的专业知识，
用通俗易懂的语言向用户解释数据含义，但**不要直接给出买卖建议**。

当用户询问某只股票时，你应该：
1. 调用工具获取最新数据
2. 检索知识库中相关指标的解释
3. 用生活化的比喻解释专业术语（如"RSI超过70就像体温过高，可能要降温"）
4. 列出关键数据供用户参考
5. 提醒用户"以上分析基于公开数据，不构成投资建议"

【日期参数处理规则】
- 所有工具的日期参数格式为 YYYYMMDD（如 20250622）。
- 当用户说“最近一个月”、“近一周”、“今年以来”时，你必须将其转换为具体的起止日期。
- 当用户说“最近”而未指定具体天数时，默认使用最近 30 天。
- 当用户未指定日期时，使用默认值（工具会自动采用最新日期）。
- 转换后的日期必须严格为 8 位数字字符串。

【转换示例】
- “最近一周” → 结束日期 = 今天，开始日期 = 7 天前
- “最近一个月” → 结束日期 = 今天，开始日期 = 30 天前
- “今年以来” → 开始日期 = 当年 1 月 1 日，结束日期 = 今天
- “帮我分析茅台” → 不需要传日期参数，工具自动使用最新日期

"""

def get_tools_description():
    tools_desc = []
    for name, info in TOOLS.items():
        tools_desc.append({
            "type": "function",
            "function": {
                "name": name,
                "description": info["description"],
                "parameters": info["parameters"]
            }
        })
    return tools_desc

def run_agent(user_query: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query}
    ]

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=get_tools_description(),
        temperature=0.1
    )

    assistant_msg = response.choices[0].message

    if assistant_msg.tool_calls:
        for tool_call in assistant_msg.tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"🔧 调用工具: {tool_name}, 参数: {arguments}")

            if tool_name in TOOLS:
                result = TOOLS[tool_name]["function"](**arguments)
            else:
                result = {"error": f"未知工具: {tool_name}"}

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False)
            })

        final_response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.3
        )
        return final_response.choices[0].message.content

    return assistant_msg.content

if __name__ == "__main__":
    query = input("请输入你的问题: ")
    answer = run_agent(query)
    print("\n🤖 助手回答:\n", answer)