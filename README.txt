# MiniQuant - 透明量化投研助手

基于公开稳定数据，通过自研量化引擎与大语言模型，实现自然语言驱动的策略研究与验证工具。

## 核心特色

- **数据透明**：全部使用 Tushare/yfinance 等公开数据源，来源可追溯
- **逻辑透明**：因子公式、回测规则全部开源，可自行验证
- **过程透明**：Agent 每一步调用了什么工具、返回了什么数据，清晰展示
- **无主观建议**：只解读数据，不给出买卖建议，最终决策由用户做出
- **通俗易懂**：结合金融知识库，用生活化比喻解释专业指标
- **自然语言交互**：通过 Dify 接入，支持手机/电脑对话式操作

## 系统架构

```
用户自然语言提问
        ↓
  Dify Agent（意图识别 + 工具调度）
        ↓
  FastAPI 工具层（8个量化工具）
        ↓
┌───────┼───────┬───────┬───────┐
↓       ↓       ↓       ↓       ↓
行情    基本面   因子   回测   特征画像
查询    查询    计算   引擎   分析
```

## 功能模块

### 1. 单股票量化分析
- 技术指标深度分析（RSI/MACD/KDJ历史分位、极端值检测、背离识别）
- 因子有效性检验（IC值、IC_IR、分层回测、因子自相关）
- 信号统计验证（金叉/死叉/RSI超卖/布林带信号历史胜率）
- 风险分析（VaR/CVaR/波动率锥/最大回撤及恢复分析）
- 行业横向对比（自动匹配同行，估值和因子排名）

### 2. 多因子组合回测
- 10+自研因子（动量、波动率、反转、RPV、新动量、综合量价、PE、PB、AI情绪）
- 可自定义因子权重，支持基本面因子
- 预加载全量行情与估值数据，内存缓存加速
- 完整的持仓明细、因子暴露、绩效归因展示

### 3. Agent 工具集（8个工具）
| 工具 | 功能 |
|------|------|
| get_stock_data | 获取股票日线行情 |
| get_fundamental | 获取基本面数据（PE/PB/ROE等） |
| get_stock_profile | 六维特征画像（趋势/波动/量价/技术/相对强弱/基本面） |
| factor_validation | 因子有效性检验（IC值/分层回测） |
| signal_backtest | 信号胜率统计（金叉/死叉/RSI/布林带） |
| risk_analysis | 风险分析（VaR/CVaR/波动率锥/回撤） |
| industry_compare | 同行业自动对比（估值/因子排名） |
| smart_analysis | LLM智能分析（新闻+量化综合） |

### 4. 数据管理
- 统一 DataManager 单例模式，内存缓存避免重复磁盘I/O
- A股/美股自动识别，路由到不同数据源
- Tushare（行情/基本面/资金流向）+ yfinance（美股）+ Finnhub（美股新闻）
- 本地 SQLite + JSON 缓存，支持离线查询

## 技术栈

| 层级 | 技术 |
|------|------|
| 数据采集 | Tushare Pro、yfinance、Finnhub |
| 数据处理 | Pandas、NumPy、SciPy |
| 因子与回测 | 自研事件驱动引擎 |
| Agent 框架 | FastAPI、Pydantic、LangChain |
| 大模型 | DeepSeek API、Ollama（本地Gemma） |
| 平台集成 | Dify（工作流）、Streamlit（调试后台） |
| 数据库 | SQLite（本地缓存） |
| 可视化 | Plotly、Matplotlib |

## 快速开始

### 1. 环境配置
```bash
pip install -r requirements.txt
```

### 2. 设置环境变量
```bash
export TUSHARE_TOKEN="你的Tushare Token"
export DEEPSEEK_API_KEY="你的DeepSeek Key"      # 可选
export FINNHUB_API_KEY="你的Finnhub Key"        # 可选
```

### 3. 初始化数据库
```bash
python -c "from intelligence.local_db import init_db; init_db()"
```

### 4. 启动 Agent API 服务
```bash
python -m agent.api
```
服务运行在 `http://localhost:8001`，Swagger 文档在 `/docs`。

### 5. 启动 Streamlit 调试界面（可选）
```bash
streamlit run app.py
```

### 6. 接入 Dify
- 将 `http://localhost:8001` 暴露到公网（使用 ngrok 等工具）
- 在 Dify 中导入 OpenAPI 规范（`/openapi.json`）
- 创建 Agent 应用，配置 System Prompt 和金融知识库

### 7. 配置代理（如 Finnhub 无法直连）
```bash
set HTTP_PROXY=http://127.0.0.1:7890
set HTTPS_PROXY=http://127.0.0.1:7890
```

## 数据源说明

| 数据类 | 来源 | 说明 |
|--------|------|------|
| A股行情 | Tushare | 日线 OHLCV，2000积分免费 |
| A股基本面 | Tushare | PE、PB、ROE、营收等 |
| A股资金流向 | Tushare | 主力净买入、超大单 |
| A股新闻 | Tushare | 个股新闻标题 |
| 行业分类 | Tushare | 全市场股票行业映射 |
| 美股行情 | yfinance | 免费，数据可靠 |
| 美股新闻 | Finnhub | 免费额度60次/分钟 |
| 沪深300基准 | Tushare | 指数日线行情 |

## 项目思考与 AI 协作

本项目大量使用 AI 编程助手。在实践中形成了以下理解：

1. **AI 能拔高代码的下限**：快速生成能跑的框架，跨过"从0到1"的阶段。
2. **代码上限由人决定**：架构设计、逻辑审查、边界处理、性能优化——这些只能由人来完成。
3. **从"使用者"到"驾驭者"**：关键不是记住语法，而是理解逻辑、判断对错、设计解决方案。

> 更多项目迭代历程和技术决策记录，请参阅 [THINKING.md](THINKING.md)

## 后续规划

- [ ] 完善 Dify 知识库（技术指标、估值指标通俗解释）
- [ ] 引入更多因子（波动率锥、偏度、峰度）
- [ ] 支持多轮对话参数调整与图表生成
- [ ] 增加策略优化工具（网格搜索最优权重）
- [ ] 行业分类扩展为全市场动态匹配

## 免责声明

本工具仅用于研究和学习目的，所有分析基于公开数据，不构成任何投资建议。使用者应独立判断并承担投资风险。