# 📚 多模态企业知识库 RAG 系统

基于大模型的企业内部知识库智能问答系统，支持多格式文档上传、智能检索、多轮对话、权限管理。

## 技术栈

| 层 | 技术 |
|---|------|
| **后端** | Python 3.12 + FastAPI (async) |
| **数据库** | PostgreSQL 16 + pgvector |
| **LLM** | DashScope（通义千问）/ DeepSeek / OpenAI |
| **嵌入** | BGE-M3 / text-embedding-v3 |
| **前端** | Vue 3 + Element Plus + Pinia |
| **队列** | Celery + RabbitMQ |
| **存储** | MinIO (S3 兼容对象存储) |
| **部署** | Docker Compose |

## 快速启动

### 前置条件

- Docker & Docker Compose
- 通义千问 API Key（[注册获取](https://help.aliyun.com/zh/dashscope/)）

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入 DASHSCOPE_API_KEY 等配置
```

### 2. 启动所有服务

```bash
docker-compose up -d
```

### 3. 访问系统

- 前端页面：`http://localhost`
- API 文档：`http://localhost/api/docs`
- 后端：`http://localhost:8000`
- 管理后台：`http://localhost/admin`

### 4. 默认账号

| 角色 | 用户名 | 密码 |
|------|-------|------|
| 管理员 | admin | admin123456 |
| 普通用户 | 注册获取 | - |

## 本地开发（不依赖 Docker）

### 后端

```bash
# 安装依赖
cd backend
pip install -r requirements.txt

# 确保 PostgreSQL 已安装并启用 pgvector
# 执行 scripts/init_db.sql 初始化数据库

# 启动
uvicorn main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

## 项目结构

```
.
├── docker-compose.yml       # 一键部署
├── backend/                 # FastAPI 后端
│   ├── main.py              # 主入口 + 路由注册
│   ├── config.py            # 配置中心
│   ├── api/                 # API 路由层
│   ├── core/                # RAG 核心逻辑
│   ├── services/            # 外部服务封装（LLM/Embedding/解析）
│   ├── db/                  # 数据层（模型/会话）
│   ├── schemas/             # Pydantic 模型
│   ├── tasks/               # Celery 后台任务
│   └── utils/               # 工具函数
├── frontend/                # Vue3 前端
├── nginx/                   # Nginx 反向代理配置
└── scripts/                 # 初始化 SQL 脚本
```

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/login` | 用户登录 |
| POST | `/api/register` | 用户注册 |
| GET | `/api/verify` | Token 验证 |
| POST | `/api/chat/send` | 发送消息（SSE 流式） |
| GET | `/api/chat/conversations` | 会话列表 |
| POST | `/api/documents/upload` | 上传文档 |
| GET | `/api/documents/list` | 文档列表 |
| GET | `/api/health` | 健康检查 |

## 许可

MIT
## LangChain 集成

系统采用渐进式 LangChain 架构：

- backend/langchain_app/retriever.py：将现有权限过滤和混合检索包装为 BaseRetriever
- backend/langchain_app/prompts.py：使用 ChatPromptTemplate 和 MessagesPlaceholder
- backend/langchain_app/models.py：使用 ChatOpenAI 接入 DeepSeek，并通过 Runnable fallback 切换 Qwen
- backend/langchain_app/chains.py：通过 Runnable Sequence 和 astream() 输出流式回答
- 图片和图表继续通过现有 Qwen-VL 多模态网关处理
- PostgreSQL 权限 SQL、SSE 协议、数据库模型和前端保持兼容

Docker 使用 backend/wheels 中的 Linux wheels 离线安装 LangChain，避免容器网络不可用导致构建失败。
