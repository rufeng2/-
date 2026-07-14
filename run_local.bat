@echo off
chcp 65001 >nul
title 企业知识库 RAG 系统

echo ========================================
echo   企业知识库 RAG 系统 - 本地启动
echo ========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] Python 未安装
    pause
    exit /b 1
)

:: 检查 Docker
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] Docker Desktop 未运行，请先启动 Docker Desktop
    pause
    exit /b 1
)

:: 检查 PostgreSQL 是否已在运行
docker ps --filter "name=rag-pg-local" --format "{{.Names}}" | findstr "rag-pg-local" >nul
if %errorlevel% neq 0 (
    echo [1/4] 启动 PostgreSQL（pgvector）...
    docker run -d ^
        --name rag-pg-local ^
        -e POSTGRES_USER=ragadmin ^
        -e POSTGRES_PASSWORD=ragadmin123 ^
        -e POSTGRES_DB=knowledge_rag ^
        -p 5432:5432 ^
        pgvector/pgvector:pg16
    echo   等待 PostgreSQL 就绪...
    :wait_pg
    timeout /t 3 /nobreak >nul
    docker exec rag-pg-local pg_isready -U ragadmin >nul 2>&1
    if %errorlevel% neq 0 goto wait_pg
    echo   ✓ PostgreSQL 就绪
) else (
    echo [1/4] PostgreSQL 已在运行
)

:: 初始化数据库
echo [2/4] 初始化数据库表...
docker cp scripts\init_db.sql rag-pg-local:/init_db.sql
docker exec -i rag-pg-local psql -U ragadmin -d knowledge_rag -f /init_db.sql >nul 2>&1
echo   ✓ 数据库初始化完成

:: 安装 Python 依赖
echo [3/4] 检查 Python 依赖...
cd /d "%~dp0"
pip install -r backend\requirements.txt -q
echo   ✓ 依赖检查完成

:: 启动后端
echo [4/4] 启动后端服务...
echo.
echo ========================================
echo   服务地址
echo   后端 API:  http://127.0.0.1:8000
echo   API 文档:  http://127.0.0.1:8000/docs
echo   OpenAPI:   http://127.0.0.1:8000/openapi.json
echo ========================================
echo.
cd /d "%~dp0backend"
set DATABASE_URL=postgresql+asyncpg://ragadmin:ragadmin123@localhost:5432/knowledge_rag
set LLM_MODEL=deepseek-chat

uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level info

pause
