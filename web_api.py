from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from agent_server import graph
from langchain_core.messages import HumanMessage
from langgraph.types import Command

app = FastAPI(title="智能客服小助 API")


class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"


@app.post("/chat")
def chat(req: ChatRequest):
    config = {"configurable": {"thread_id": req.thread_id}}
    result = graph.invoke(
        {"messages": [HumanMessage(content=req.message)]},
        config=config,
    )
    while "__interrupt__" in result:
        result = graph.invoke(Command(resume="yes"), config=config)
    return {"reply": result["messages"][-1].content}


@app.get("/", response_class=HTMLResponse)
def index():
    return """
<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>智能客服小助</title>
<style>
  body { font-family: -apple-system, "Microsoft YaHei", sans-serif; background:#f5f6f8; margin:0; }
  .wrap { max-width: 720px; margin: 0 auto; height: 100vh; display:flex; flex-direction:column; }
  h2 { text-align:center; padding:16px 0; margin:0; background:#fff; border-bottom:1px solid #eee; }
  #chat { flex:1; overflow-y:auto; padding:16px; }
  .msg { margin:8px 0; display:flex; }
  .msg.user { justify-content:flex-end; }
  .bubble { max-width:75%; padding:10px 14px; border-radius:12px; white-space:pre-wrap; line-height:1.5; }
  .user .bubble { background:#4f7cff; color:#fff; }
  .ai .bubble { background:#fff; color:#222; border:1px solid #eee; }
  .bar { display:flex; gap:8px; padding:12px; background:#fff; border-top:1px solid #eee; }
  #msg { flex:1; padding:10px 12px; border:1px solid #ddd; border-radius:8px; font-size:15px; }
  button { padding:10px 20px; border:none; border-radius:8px; background:#4f7cff; color:#fff; font-size:15px; cursor:pointer; }
  button:disabled { opacity:.5; cursor:not-allowed; }
</style>
</head>
<body>
<div class="wrap">
  <h2>智能客服小助</h2>
  <div id="chat">
    <div class="msg ai"><div class="bubble">您好！我是智能客服小助，有什么可以帮您？</div></div>
  </div>
  <div class="bar">
    <input id="msg" placeholder="输入消息，回车发送..." autocomplete="off">
    <button id="send" onclick="send()">发送</button>
  </div>
</div>
<script>
  const chat = document.getElementById('chat');
  const input = document.getElementById('msg');
  const btn = document.getElementById('send');
  const threadId = 'web-' + Math.random().toString(36).slice(2, 8);

  function add(role, text) {
    const d = document.createElement('div');
    d.className = 'msg ' + role;
    const b = document.createElement('div');
    b.className = 'bubble';
    b.textContent = text;
    d.appendChild(b);
    chat.appendChild(d);
    chat.scrollTop = chat.scrollHeight;
    return b;
  }

  async function send() {
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    add('user', text);
    const thinking = add('ai', '正在思考...');
    btn.disabled = true;
    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({message: text, thread_id: threadId})
      });
      const data = await res.json();
      thinking.textContent = data.reply;
    } catch (e) {
      thinking.textContent = '出错了：' + e;
    }
    btn.disabled = false;
    input.focus();
  }

  input.addEventListener('keydown', e => { if (e.key === 'Enter') send(); });
  input.focus();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)