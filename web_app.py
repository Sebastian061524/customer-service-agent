import gradio as gr
from agent_server import graph
from langchain_core.messages import HumanMessage
from langgraph.types import Command

def chat(message, history):
    config = {"configurable": {"thread_id": "web-user"}}
    result = graph.invoke(
        {"messages": [HumanMessage(content=message)]},
        config=config,
    )
    # 简化：网页版自动批准所有审批
    while "__interrupt__" in result:
        result = graph.invoke(Command(resume="yes"), config=config)

    return result["messages"][-1].content

gr.ChatInterface(fn=chat, title="智能客服小助").launch()