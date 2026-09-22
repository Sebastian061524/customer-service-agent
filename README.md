# 智能客服 Agent「小助」

一个基于 **LangGraph** 的智能客服助手，实现了 **RAG 知识问答、多工具调用、人工审批（Human-in-the-loop）、多轮记忆持久化**，并配套 **可观测性** 与 **自动化评测**。

## ✨ 功能特性

- **RAG 知识问答**：基于 `BAAI/bge-small-zh-v1.5` 中文嵌入模型 + 关键词/向量混合检索，回答产品、政策类问题
- **多工具调用**：算价（`calculate`）、查时间（`get_current_time`）、下单（`place_order`）
- **人工审批（Human-in-the-loop）**：敏感操作执行前通过 LangGraph `interrupt` 暂停图，等待人工批准后才继续
- **多轮记忆**：基于 SQLite checkpointer，对话历史跨进程持久化
- **全链路可观测**：接入 Langfuse，追踪每一步 LLM 调用、工具执行、耗时与 token 消耗
- **质量评测**：18 题评测集 + LLM-as-judge 自动评分

## 🏗️ 架构

```
用户
 ↓
Web 前端（Gradio / HTML）
 ↓
FastAPI  /chat 接口
 ↓
LangGraph Agent（ReAct 循环）
 ├─ retrieve     RAG 混合检索，注入相关知识
 ├─ chatbot      LLM 决策：直接回答 or 调用工具
 ├─ approval     人工审批（interrupt 暂停）
 ├─ tools        执行工具
 └─ chatbot      基于工具结果给出最终回答
 ↓
DeepSeek 大模型 API
```

图结构的关键是 `tools → chatbot` 这条**回边**，构成了 ReAct 的「推理-行动-观察」循环，使 Agent 能多步推理（例如「3+5+7」会连续调用两次计算工具）。

## 🔧 技术栈

| 类别 | 技术 |
|---|---|
| Agent 框架 | LangGraph、LangChain |
| 大模型 | DeepSeek（`deepseek-chat`） |
| 嵌入模型 | `BAAI/bge-small-zh-v1.5`（本地运行） |
| 可观测性 | Langfuse |
| Web 服务 | FastAPI、Uvicorn |
| 快速界面 | Gradio |
| 存储 | SQLite |

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置密钥

复制 `.env.example` 为 `.env`，填入你自己的密钥：

```bash
copy .env.example .env      # Windows
cp .env.example .env        # macOS / Linux
```

`.env` 内容：

```
DEEPSEEK_API_KEY=sk-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://us.cloud.langfuse.com
```

### 3. 运行

**命令行模式**
```bash
python agent_server.py
```

**Web 服务（推荐）**
```bash
python web_api.py
```
- 聊天界面：http://127.0.0.1:8000/
- API 文档：http://127.0.0.1:8000/docs

**Gradio 界面**
```bash
python web_app.py
```

### 4. 跑评测

```bash
python eval_agent.py
```

## 📊 评测结果

评测集覆盖 4 类场景，使用 LLM-as-judge 自动评分：

| 测试类型 | 题数 | 说明 |
|---|---|---|
| 基础事实 | 10 | 产品价格、退换货政策、发货时效等 |
| 计算 / 优惠 | 6 | 原价计算、满减判断、会员折扣 |
| 超纲拒答 | 2 | 知识库没有的内容，应诚实说「不知道」而非编造 |
| **合计** | **18** | **通过率 100%** |

## 📁 项目结构

```
.
├── agent_server.py        # Agent 核心（LangGraph 图定义）
├── web_api.py             # FastAPI 服务 + 内嵌聊天前端
├── web_app.py             # Gradio 界面
├── eval_agent.py          # 评测脚本（18 题 + LLM 裁判）
├── customer_service.txt   # 知识库
├── requirements.txt       # 依赖
├── .env.example           # 环境变量模板
└── .gitignore
```

## 🔍 关键实现说明

### 人工审批（interrupt）

敏感操作（如下单）不能自动执行。在 `approval` 节点调用 `interrupt()` 暂停图，由调用方决定是否继续：

```python
def approval(state: State):
    last = state["messages"][-1]
    desc = [(tc["name"], tc["args"]) for tc in last.tool_calls]
    answer = interrupt(f"要执行这些工具吗？{desc}\n输入 yes 批准，no 取消：")
    if answer == "yes":
        return {"approved": True}
    # 取消时，必须为每个 tool_call 补一条 ToolMessage，
    # 否则消息历史非法（tool_calls 后面缺少 tool 响应）
    cancelled = [
        ToolMessage(content="用户取消了执行", tool_call_id=tc["id"])
        for tc in last.tool_calls
    ]
    return {"approved": False, "messages": cancelled}
```

### 混合检索

单纯向量检索对「产品编号」这类无语义内容效果差，单纯关键词检索又无法处理同义词。因此采用两者合并去重：

```python
def hybrid_search(query):
    kw = keyword_search(query, top_k=2)    # 精确匹配（编号、术语）
    vec = vector_search(query, top_k=3)    # 语义匹配（同义词）
    combined = []
    for r in kw + vec:
        if r not in combined:
            combined.append(r)
    return "\n\n".join(combined)
```

## 📄 License

MIT
