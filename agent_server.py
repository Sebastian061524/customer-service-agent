"""
智能客服 Agent「小助」—— 核心 Agent 逻辑

技术栈：LangGraph + LangChain + DeepSeek + BGE + Langfuse
功能：RAG 知识问答、多工具调用、人工审批、SQLite 记忆持久化
"""
import os
from dotenv import load_dotenv

# 从 .env 文件加载密钥（.env 不会被提交到 git）
load_dotenv()

# 第三方库配置（必须在导入相关库之前设置）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

from langfuse.langchain import CallbackHandler

# Langfuse 全链路追踪（密钥从环境变量读取）
langfuse_handler = CallbackHandler()
import datetime
from typing import Annotated, TypedDict
from sentence_transformers import SentenceTransformer
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver



class State(TypedDict):
    messages: Annotated[list, add_messages]
    approved: bool


llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

# 加载模型 + 索引知识库
model = SentenceTransformer("BAAI/bge-small-zh-v1.5",local_files_only=True)
with open("customer_service.txt", "r", encoding="utf-8") as f:
    content = f.read()
chunks = [c.strip() for c in content.split("\n\n") if c.strip()]
chunks_embeddings = model.encode(chunks, normalize_embeddings=True)

@tool
def calculate(a: float, b: float, op: str):
    """
    计算两个数的四则运算。
    Args:
        a: 第一个数字
        b: 第二个数字
        op: 运算符，只能是 "+"、"-"、"*"、"/" 之一
    """
    if op == "+":
        return a + b
    elif op == "-":
        return a - b
    elif op == "*":
        return a * b
    elif op == "/":
        return a / b if b != 0 else "除数不能为0"
    else:
        return "未知运算"

@tool
def get_current_time():
    """获得当前日期和时间"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@tool
def place_order(product: str, quantity: int) -> str:
    """为客户创建订单。这是一个敏感操作，会真实下单，需要谨慎。"""
    with open("orders.txt", "a", encoding="utf-8") as f:
        f.write(f"{product} x {quantity}\n")
    return f"订单已创建：{product} x {quantity}"

tools = [calculate, get_current_time, place_order]
llm_with_tools = llm.bind_tools(tools)


def keyword_search(query, top_k=2):
    matched = [c for c in chunks if query in c]
    if not matched:
        for ch in query:
            matched = [c for c in chunks if ch in c]
            if matched:
                break
    return matched[:top_k]

def vector_search(query, top_k=3):
    query_vec = model.encode(query, normalize_embeddings=True)
    scores = chunks_embeddings @ query_vec
    top_idx = scores.argsort()[::-1][:top_k]
    return [chunks[i] for i in top_idx]

def hybrid_search(query):
    kw = keyword_search(query, top_k=2)
    vec = vector_search(query, top_k=3)
    combined = []
    for r in kw + vec:
        if r not in combined:
            combined.append(r)
    return "\n\n".join(combined)

def chatbot(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

# 检索节点：在 chatbot 之前跑，把相关知识注入
def retrieve(state: State):
    user_msg = state["messages"][-1].content      # 用户最后的问题
    knowledge = hybrid_search(user_msg)            # 你之前写的混合检索
    # 把知识作为 system 提示注入
    from langchain_core.messages import SystemMessage
    return {"messages": [SystemMessage(content=f"参考知识：\n{knowledge}")]}

def approval(state: State):
    last = state["messages"][-1]
    desc = [(tc["name"], tc["args"]) for tc in last.tool_calls]
    answer = interrupt(f"要执行这些工具吗？{desc}\n输入 yes 批准，no 取消：")
    if answer == "yes":
        return {"approved": True}
    else:
        cancelled = [
            ToolMessage(content="用户取消了执行", tool_call_id=tc["id"])
            for tc in last.tool_calls
        ]
        return {"approved": False, "messages": cancelled}   # 注意：返回 messages！

def route_after_chatbot(state):
    if state["messages"][-1].tool_calls:
        return "approval"       # 有工具调用 → 审批
    return "end"                # 没有 → 结束

def route_after_approval(state):
    if state["approved"]:
        return "tools"          # 批准 → 执行
    return "chatbot"            # 拒绝 → 回 chatbot 回应取消


builder = StateGraph(State)
builder.add_node("retrieve", retrieve)
builder.add_node("chatbot", chatbot)
builder.add_node("approval", approval)
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "retrieve")
builder.add_edge("retrieve", "chatbot")
builder.add_conditional_edges("chatbot", route_after_chatbot, {"approval": "approval", "end": END})
builder.add_conditional_edges("approval", route_after_approval, {"tools": "tools", "chatbot": "chatbot"})
builder.add_edge("tools", "chatbot")


# ① 直接建立连接（不用 with，连接会一直开着）
conn = sqlite3.connect("customer_service.db", check_same_thread=False)

# ② 用连接创建 checkpointer
checkpointer = SqliteSaver(conn)

# ③ 编译图（现在 graph 在模块顶层，可以被 import）
graph = builder.compile(checkpointer=checkpointer)


if __name__ == "__main__":
    # 命令行交互模式（只在直接运行本文件时执行）
    config = {"configurable": {"thread_id": "main"}}
    while True:
        user_input = input("你：")
        if user_input.lower() in ["exit", "退出"]:
            break
        result = graph.invoke({"messages": [HumanMessage(content=user_input)]}, config=config)

        while "__interrupt__" in result:
            prompt = result["__interrupt__"][0].value
            answer = input(f"\n{prompt}")
            result = graph.invoke(Command(resume=answer), config=config)

        print("AI：", result["messages"][-1].content)





