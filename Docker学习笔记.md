# Docker 学习笔记

> 从零到容器化一个真实的 AI Agent 应用
> 学习时间：2026 年

---

## 目录

- [一、核心概念](#一核心概念)
- [二、常用命令速查](#二常用命令速查)
- [三、Dockerfile 详解](#三dockerfile-详解)
- [四、本项目的容器化](#四本项目的容器化)
- [五、常见问题与坑](#五常见问题与坑)
- [六、实战踩坑记录（真实案例）](#六实战踩坑记录真实案例)

---

## 一、核心概念

### 1.1 为什么需要 Docker

**问题**：换台电脑就报错——Python 版本不对、缺依赖、环境变量没配……

**Docker 解决的就是这个问题**：把应用**连同运行环境一起打包**，在任何机器上都能一模一样地跑起来。

```
传统方式：你的代码 → 依赖别人的环境
Docker：  你的代码 + 运行环境 → 打包成「集装箱」→ 到处能跑
```

### 1.2 镜像 vs 容器（最重要的概念）

| | 镜像（Image） | 容器（Container） |
|---|---|---|
| 是什么 | **只读的模板** | **运行中的实例** |
| 类比 | 类（class）/ 菜谱 / 安装包 | 对象 / 做出来的菜 / 装好的程序 |
| 关系 | 一个镜像 → 可启动**多个**容器 | 每个容器相互独立 |
| 状态 | 静态、不可修改 | 动态、可修改 |

```
镜像 nginx（只存一份）
   ├── 容器 A   my-nginx      ← stop 停它、rm 删它
   ├── 容器 B   nginx-2       ← 同一个镜像可开多个容器
   └── 容器 C   nginx-3
```

### 1.3 三者的关系

```
Dockerfile  ──docker build──►  镜像(Image)  ──docker run──►  容器(Container)
 （说明书）                     （成品模板）                 （运行中的实例）
```

| 概念 | 一句话 |
|---|---|
| Dockerfile | 构建镜像的说明书 |
| 镜像 | 只读模板（类） |
| 容器 | 运行实例（对象） |

### 1.4 三种操作的区别

| 命令 | 作用 | 影响镜像 | 影响容器 |
|---|---|---|---|
| `docker stop` | 停止容器（容器还在，状态变 Exited） | ❌ | ✅ 停止运行 |
| `docker rm` | 删除容器（彻底消失） | ❌ | ✅ 消失 |
| `docker rmi` | 删除镜像 | ✅ 消失 | ❌ 已存在的容器还能跑，但不能开新容器 |

---

## 二、常用命令速查

### 2.1 操作容器

```bash
docker run -d --name my-app -p 8000:8000 my-image   # 启动容器
docker ps                                            # 看运行中的容器
docker ps -a                                         # 看所有容器（含已停止）
docker stop my-app                                   # 停止
docker start my-app                                  # 启动已停止的容器
docker rm my-app                                     # 删除容器
docker logs my-app                                   # 看日志（调试必备）
docker logs -f my-app                                # 实时跟踪日志
docker exec -it my-app bash                          # 进入容器内部
```

### 2.2 操作镜像

```bash
docker images                 # 列出本地镜像
docker pull nginx             # 下载镜像
docker build -t my-image .    # 从 Dockerfile 构建镜像
docker rmi my-image           # 删除镜像
docker history my-image       # 看镜像的层结构
```

### 2.3 `docker run` 常用参数

| 参数 | 作用 | 示例 |
|---|---|---|
| `-d` | 后台运行（不占用终端） | `docker run -d nginx` |
| `-p 主机:容器` | 端口映射 | `-p 8080:80` |
| `--name xxx` | 给容器起名 | `--name my-nginx` |
| `-e KEY=VALUE` | 设置环境变量 | `-e APP_ENV=dev` |
| `--env-file .env` | 从文件加载环境变量 | `--env-file .env` |
| `-v 主机:容器` | 挂载数据卷（持久化） | `-v ./data:/app/data` |
| `-it` | 交互式终端 | `docker run -it ubuntu bash` |
| `--rm` | 容器退出后自动删除 | `--rm` |
| `restart` | 退出策略 | `--restart unless-stopped` |

### 2.4 端口映射原理

```
-p 主机端口:容器端口
   8080  :  80

你的电脑 :8080  ──映射──►  容器内部 :80
（浏览器访问）              （nginx 监听）
```

**口诀**：`-p` **左边是你的电脑，右边是容器内部**。左边随便定，右边必须是容器的真实端口。

### 2.5 Docker Compose

```bash
docker compose up -d        # 启动所有服务（后台）
docker compose down         # 停止并删除
docker compose logs -f      # 看日志
docker compose ps           # 看状态
docker compose build        # 重新构建
```

---

## 三、Dockerfile 详解

### 3.1 指令全景图

Dockerfile 指令分**两类**——这是理解一切的基础：

| 类别 | 什么时候执行 | 指令 |
|---|---|---|
| **构建时**（BUILD） | `docker build` 时执行一次，结果成为镜像 | `FROM` `WORKDIR` `COPY` `ADD` `RUN` `ARG` |
| **运行时**（RUNTIME） | `docker run` 时每次执行 | `CMD` `ENTRYPOINT` `EXPOSE` `ENV` `VOLUME` `USER` `HEALTHCHECK` |

### 3.2 最容易混淆的概念

#### `RUN` vs `CMD` vs `ENTRYPOINT`

```dockerfile
RUN  echo "构建时执行"              # build 时执行一次，「烤」进镜像
CMD  ["echo", "容器启动时执行"]      # run 时执行，可被覆盖
ENTRYPOINT ["echo", "入口命令"]      # run 时执行，不易被覆盖
```

**`RUN` vs `CMD` 的类比**：

```
RUN = 装修房子   → 做完就固定了，成为房子的一部分（只做一次）
CMD = 开门营业   → 每次开店都要做（容器每次启动都执行）
```

典型用法：
```dockerfile
RUN pip install flask      # 装依赖 → RUN
CMD ["python", "app.py"]   # 启动服务 → CMD
```

**`CMD` vs `ENTRYPOINT`**：

```dockerfile
# CMD 可被 docker run 后面的命令覆盖
CMD ["python", "app.py"]
# docker run myimage python other.py  →  执行 python other.py

# ENTRYPOINT 不会被覆盖，后面参数变成它的参数
ENTRYPOINT ["python"]
CMD ["app.py"]
# docker run myimage other.py  →  执行 python other.py
```

经典组合：**`ENTRYPOINT` 定程序，`CMD` 定默认参数**
```dockerfile
ENTRYPOINT ["uvicorn"]
CMD ["app:app", "--host", "0.0.0.0", "--port", "8000"]
```

> 应用容器用 `CMD` 即可；工具类镜像用 `ENTRYPOINT` + `CMD`。

#### `COPY` vs `ADD`

```dockerfile
COPY app.py .        # ✅ 推荐：单纯复制
ADD  app.tar.gz .    # ⚠️ 会自动解压、支持 URL —— 行为不直观，少用
```

**规则：优先用 `COPY`。**

#### `ENV` vs `ARG`

```dockerfile
ARG VERSION=1.0           # 构建时变量：build 时可传，镜像里不保留
ENV APP_ENV=production    # 运行时环境变量：保留在镜像里
```

```bash
docker build --build-arg VERSION=2.0 .   # 传 ARG
docker run -e APP_ENV=dev myimage        # 覆盖 ENV
```

- `ARG` → 控制**构建过程**
- `ENV` → 给**运行的应用**提供配置

#### `EXPOSE` 的真实作用

```dockerfile
EXPOSE 8000
```

**它不会真的开放端口！** 只是文档说明。真正开放靠 `docker run -p`。

### 3.3 层缓存原理

镜像是**一层一层叠**起来的：

```dockerfile
FROM python:3.12-slim        ← 层 1
WORKDIR /app                 ← 层 2
COPY requirements.txt .      ← 层 3
RUN pip install -r ...       ← 层 4  （慢！）
COPY app.py .                ← 层 5
CMD [...]                    ← 层 6
```

> **核心规则：某一层变了，它和它之后的所有层都要重建。**

**所以顺序很重要**：

```dockerfile
# ❌ 坏顺序
COPY . .
RUN pip install -r requirements.txt
# 改了 app.py → COPY . . 变了 → pip install 重跑（几分钟）

# ✅ 好顺序
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
# 改了 app.py → 只有最后一层变 → pip install 用缓存（几秒）
```

**口诀**：**变化少的放前面，变化多的放后面。**

**同层合并技巧**：
```dockerfile
# ❌ 三条层
RUN apt-get update
RUN apt-get install -y git
RUN rm -rf /var/lib/apt/lists/*

# ✅ 一条层
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
```

### 3.4 黄金法则

| # | 法则 | 原因 |
|---|---|---|
| 1 | 用精简基础镜像（`-slim` / `-alpine`） | 体积小、攻击面小 |
| 2 | 合并 `RUN` 命令 | 减少层数、减小体积 |
| 3 | 变化少的放前面 | 利用缓存，加快构建 |
| 4 | 写好 `.dockerignore` | 别把 `.git`/`.env`/缓存传进构建 |
| 5 | **密钥绝不进镜像** | 用 `--env-file` 运行时注入 |
| 6 | 固定版本（`python:3.12.1` 而非 `:latest`） | 保证可复现 |
| 7 | 非 root 用户运行 | 安全 |
| 8 | 一个容器一个进程 | 便于扩展和管理 |

**法则 7 示例**：
```dockerfile
RUN useradd -m appuser
USER appuser
```

### 3.5 多阶段构建（Multi-stage Build）

**问题**：构建需要编译器，运行时不需要——留着就是浪费。

```dockerfile
# ===== 阶段 1：构建（不会进最终镜像）=====
FROM python:3.12 AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# ===== 阶段 2：运行（只复制需要的东西）=====
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY app.py .
CMD ["python", "app.py"]
```

```
单阶段镜像：1.2 GB（含编译器、缓存）
多阶段镜像：200 MB（只有运行必需的）
```

适用于：Go / Rust / C++ 等编译型语言、React / Vue 等前端项目。

### 3.6 常用模板

#### Python Web 应用

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Node.js 应用

```dockerfile
FROM node:20-slim
WORKDIR /app
COPY package*.json ./
RUN npm install --production
COPY . .
EXPOSE 3000
CMD ["node", "server.js"]
```

#### 生产级（含非 root 用户）

```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN useradd -m appuser
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3.7 写 Dockerfile 的思考顺序

```
1. 用什么基础镜像？          → FROM
2. 工作目录在哪？            → WORKDIR
3. 需要装什么系统依赖？      → RUN apt-get ...
4. 需要装什么语言依赖？      → COPY 清单 + RUN pip install
5. 复制应用代码              → COPY
6. 怎么启动？                → CMD
```

---

## 四、本项目的容器化

### 4.1 Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# ① 先装 CPU 版 PyTorch
#    关键：Linux 上默认会拉 CUDA 版（2.5GB+），指定 CPU 源降到 ~200MB
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# ② 再装其余依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# ③ 预下载嵌入模型（构建时下载一次，运行时不用联网）
ENV HF_ENDPOINT=https://hf-mirror.com
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-zh-v1.5')"

# ④ 复制应用代码
#    故意不复制 .env —— 密钥通过 --env-file 运行时注入
COPY agent_server.py web_api.py customer_service.txt ./

EXPOSE 8000
CMD ["uvicorn", "web_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 4.2 三个关键设计决策

| 决策 | 说明 |
|---|---|
| **用 CPU 版 torch** | 体积从 2.5GB 降到 200MB |
| **预下载模型进镜像** | 镜像自包含，换机器也能跑 |
| **`.env` 不进镜像** | 密钥安全，镜像可公开 |

### 4.3 `.dockerignore`

```
.env
*.db
orders.txt
__pycache__/
.venv/
.git/
```

**作用**：构建时排除这些文件，避免密钥和数据被复制进镜像。

### 4.4 构建与运行

```bash
# 构建（约 10-25 分钟）
docker build -t customer-agent .

# 方式 A：docker run
docker run -d --name agent -p 8000:8000 --env-file .env customer-agent

# 方式 B：docker compose（推荐）
docker compose up -d
```

访问 http://localhost:8000

---

## 五、常见问题与坑

### 5.1 拉取镜像超时（国内网络）

**现象**：
```
dialing registry-1.docker.io:443: connectex: A connection attempt failed...
```

**原因**：Docker Hub 在国内被 DNS 污染。

**解决**：配置国内镜像加速

Docker Desktop → Settings → Docker Engine → 修改 JSON：

```json
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me",
    "https://dockerpull.org"
  ]
}
```

点 **Apply & Restart**。

> 国内公共镜像站经常失效，最稳的是阿里云免费专属加速器（`cr.console.aliyun.com`）。

### 5.2 容器启动了但浏览器访问不了

**排查顺序**：

1. **端口映射写了吗？** `docker run -p 8000:8000`
2. **应用监听的是 `0.0.0.0` 吗？**
   ```python
   uvicorn app:app --host 0.0.0.0   # ✅ 容器里必须用 0.0.0.0
   uvicorn app:app --host 127.0.0.1 # ❌ 容器外访问不到
   ```
3. **容器在运行吗？** `docker ps`
4. **看日志**：`docker logs <容器名>`

> **经典坑**：应用在容器里监听 `127.0.0.1`，容器外永远访问不到。必须监听 `0.0.0.0`。

### 5.3 数据丢失（容器删了数据就没了）

**容器是无状态的**——删掉容器，里面写的数据也没了。

**解决**：用数据卷挂载

```bash
docker run -v ./data:/app/data myimage
```

或在 `docker-compose.yml` 里：

```yaml
volumes:
  - ./customer_service.db:/app/customer_service.db
```

### 5.4 本地能跑，容器里报错

**常见原因**：

| 原因 | 排查 |
|---|---|
| 缺依赖 | `requirements.txt` 是否完整 |
| 文件没复制进镜像 | `.dockerignore` 是否误排除了 |
| 路径不对 | 容器内路径是 `/app/...`，不是 Windows 路径 |
| 环境变量缺失 | 是否传了 `--env-file` |

### 5.5 镜像太大

| 优化手段 | 效果 |
|---|---|
| 用 `-slim` 基础镜像 | -500MB |
| 装 CPU 版 torch | -2GB |
| 合并 RUN + 清理缓存 | -200MB |
| 多阶段构建 | -50%+ |

---

## 附：常用排查命令

```bash
docker ps -a                      # 所有容器（含已停止）
docker logs <容器>                # 看日志
docker logs -f <容器>             # 实时日志
docker exec -it <容器> bash       # 进入容器排查
docker inspect <容器>             # 看容器详细配置
docker stats                      # 看资源占用
docker system df                  # 看磁盘占用
docker system prune               # 清理无用数据（慎用）
```

---

## 六、实战踩坑记录（真实案例）

这一章记录容器化本项目时**真实遇到并解决**的三个问题。这些坑「看教程学不会，只有真做才会遇到」。

### 案例 1：容器崩溃 —— 依赖版本冲突

**现象**

```
ImportError: cannot import name 'propagate_attributes' from 'langfuse'
customer-service-agent exited with code 1 (restarting)
```

容器不断重启（`restart: unless-stopped` 让它反复尝试）。

**排查过程**

1. `docker compose logs -f` 看日志 → 定位到 `langfuse/langchain/CallbackHandler.py` 第 22 行
2. 对比本地：本地 venv 里**根本没有** `langfuse-langchain` 这个包
3. 确认：「本地没有的包，requirements 里却写了」→ 版本冲突

**根因**

```txt
requirements.txt 里同时写了：
    langfuse
    langfuse-langchain      ← 多余！

但 langfuse v4 已经内置了 langchain 集成（langfuse.langchain），
额外的 langfuse-langchain 装进来的东西与核心包冲突。
```

**修复**

- 从 `requirements.txt` 删除 `langfuse-langchain`
- 所有依赖**固定版本**

**教训**

> 不锁版本 → pip 装最新版 → 本地能跑、容器里炸。
> 这是「在我机器上能跑」的现代版本，而且更隐蔽（代码/Dockerfile 都没错）。

---

### 案例 2：容器崩溃 —— 漏了间接依赖

**现象**

```
ModuleNotFoundError: No module named 'langgraph.checkpoint.sqlite'
```

**排查过程**

1. 代码里明明写了 `from langgraph.checkpoint.sqlite import SqliteSaver`
2. 但 `requirements.txt` 里只有 `langgraph`
3. 查本地 venv：`pip list | findstr langgraph`，发现有 `langgraph-checkpoint-sqlite`

**根因**

```txt
langgraph.checkpoint.sqlite 这个模块
    ↑ 不属于 langgraph 包！
    ↑ 来自单独的包 langgraph-checkpoint-sqlite
```

**修复**

```txt
langgraph==1.2.11
langgraph-checkpoint==4.2.0
langgraph-checkpoint-sqlite==3.1.1     ← 补上这个
langgraph-prebuilt==1.1.0
```

**教训**

> **包 ≠ 模块。** 一个 `import` 语句可能对应你完全没想到的包。
> 靠记忆列依赖一定会漏。
>
> **可靠做法**：`pip freeze > requirements.txt`（导出完整清单）
> - 开发阶段：手动维护主要依赖（简洁）
> - 部署之前：`pip freeze` 导出完整清单（保证一致）

---

### 案例 3：镜像重复，白占 2.55GB

**现象**

```powershell
docker images
# agent-agent:latest      2.55GB
# customer-agent:latest   2.55GB     ← 内容一样，占了两份空间
```

**根因：Docker Compose 的镜像命名规则**

```txt
<项目名>-<服务名>
    ↑        ↑
  目录名   docker-compose.yml 里 services 的名字

目录叫 agent，服务也叫 agent  →  生成了 agent-agent
```

- `customer-agent` = 手动 `docker build -t customer-agent .` 建的
- `agent-agent` = `docker compose up -d` 自动建的

**修复**

① 在 compose 里固定镜像名：

```yaml
services:
  agent:
    build: .
    image: customer-agent      # ← 指定名字，不再自动生成
```

② 删掉多余的，用 `tag` 加别名：

```powershell
docker rmi customer-agent              # 删掉重复镜像（释放空间）
docker tag agent-agent customer-agent  # 给在用的镜像加个别名
```

**附带知识：镜像的「名字」体系**

```txt
镜像 ID（唯一、不可变）：025004381643
       ↑
   多个「标签」指向同一个镜像：
       ├─ agent-agent:latest
       └─ customer-agent:latest     ← 只是两个名字，不占额外空间
```

所以 `docker rmi` 删一个有多个标签的镜像时，只会删掉一个名字。

---

### 容器调试通用流程（重要）

```
1. docker compose ps               → 容器状态（Up / Restarting / Exited）
2. docker compose logs -f          → 看报错（★ 最重要的一步）
3. 读最后一行错误                   → 通常直接写明原因
4. 和「本地能跑的 venv」对比         → 缺什么包？哪个版本不同？
5. 改 requirements.txt             → 锁定版本
6. docker compose build && up -d   → 重建验证
```

**核心心法**

> 容器报错 → **先看日志**，再**对比本地环境**。
> 90% 的容器问题都是「依赖不一致」造成的——这正是 Docker 要解决的问题，
> 而它生效的前提是：**你必须锁定版本**。

| 排错命令 | 用途 |
|---|---|
| `docker compose logs -f` | 看应用日志（首选） |
| `docker compose ps` | 看容器状态和重启次数 |
| `docker exec -it <容器> bash` | 进容器里面查（看装了什么包） |
| `docker inspect <容器>` | 看容器完整配置 |
| `docker compose config` | 检查 compose 文件是否解析正确 |

---

## 总结

```
Docker 三件套：Dockerfile → 镜像 → 容器

核心心智模型：
  镜像 = 类，容器 = 对象
  RUN = 装修（构建时），CMD = 营业（运行时）
  变化少的放前面（层缓存）
  密钥不进镜像
  容器里必须监听 0.0.0.0
```

**学会了 Docker，你就有了「把任何项目部署到任何机器」的能力。**
