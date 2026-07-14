# 启动指南

## 方式一：Docker 一键启动（推荐）

```bash
# 1. 配置 Docker 国内镜像加速（否则下不动）
```

用记事本打开 `C:\Users\34939\.docker\daemon.json`，没有就新建：

```json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://registry.docker-cn.com"
  ]
}
```

然后右击系统托盘 Docker 图标 → Restart。

```bash
# 2. 启动所有服务
cd D:\保险推荐\企业知识库问答
docker compose -p rag up -d

# 3. 访问
#    前端:    http://localhost
#    API:     http://localhost:8000
#    API文档:  http://localhost:8000/docs
```

---

## 方式二：Docker PostgreSQL + 本地后端（最快的折中方案）

```bash
# 1. 启动 PostgreSQL（只需这一步用 Docker）
docker run -d --name rag-pg ^
  -e POSTGRES_USER=ragadmin ^
  -e POSTGRES_PASSWORD=ragadmin123 ^
  -e POSTGRES_DB=knowledge_rag ^
  -p 5432:5432 ^
  pgvector/pgvector:pg16

# 2. 启动后端
cd D:\保险推荐\企业知识库问答\backend
pip install -r requirements.txt

set DATABASE_URL=postgresql+asyncpg://ragadmin:ragadmin123@localhost:5432/knowledge_rag
set DEEPSEEK_API_KEY=***
set DASHSCOPE_API_KEY=***
set SECRET_KEY=***

uvicorn main:app --reload --port 8000 --log-level info

# 3. 另开终端，启动前端
cd D:\保险推荐\企业知识库问答\frontend
npm install
npm run dev
```

---

## 方式三：纯本地开发（无需 Docker，无需 PostgreSQL）

如果 PostgreSQL 镜像实在拉不下来，可以临时改为 SQLite（会失去向量检索能力，但对话和关键词搜索能用）：

```python
# backend/db/session.py 中将数据库连接改为：
DATABASE_URL = "sqlite+aiosqlite:///./knowledge_rag.db"
```

需要安装：
```bash
pip install aiosqlite
```

然后启动后端：
```bash
cd D:\保险推荐\企业知识库问答\backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

---

## 默认账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | admin123456 |
| 普通用户 | 自行注册 | - |

## 关键环境变量

```env
# DeepSeek V4（主力模型）
DEEPSEEK_API_KEY=***

# 阿里云百炼（嵌入+看图）
DASHSCOPE_API_KEY=***

# PostgreSQL 连接
DATABASE_URL=postgresql+asyncpg://ragadmin:ragadmin123@localhost:5432/knowledge_rag
```

所有 Key 已在 `.env` 文件中配好，直接启动即可。
