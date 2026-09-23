# ============================================================
# 智能客服 Agent「小助」—— Docker 镜像
# ============================================================
FROM python:3.12-slim

WORKDIR /app

# ① 先装 CPU 版 PyTorch
#    ⚠️ 关键：Linux 上 pip install torch 默认拉 CUDA 版（2.5GB+），
#       这里指定 CPU 源，体积降到 ~200MB
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# ② 再装其余依赖（放在 torch 之后，复用它，不会重复拉 CUDA 版）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# ③ 预下载嵌入模型到镜像里（构建时下载一次，运行时就不用联网）
ENV HF_ENDPOINT=https://hf-mirror.com
ENV HF_HUB_DISABLE_SYMLINKS_WARNING=1
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-zh-v1.5')"

# ④ 复制应用代码
#    ⚠️ 故意不复制 .env —— 密钥通过 docker run --env-file 在运行时注入，
#       绝不能烤进镜像里（否则 push 到仓库就泄漏了）
COPY agent_server.py web_api.py customer_service.txt ./

# ⑤ 声明端口
EXPOSE 8000

# ⑥ 启动命令（host 必须是 0.0.0.0，否则容器外访问不到）
CMD ["uvicorn", "web_api:app", "--host", "0.0.0.0", "--port", "8000"]
