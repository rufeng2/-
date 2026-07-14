@echo off
chcp 65001 >nul
title 企业知识库 RAG 服务

echo [1/4] 启动 PostgreSQL 容器（首次需下载镜像，之后秒开）...
docker run -d --name rag-pg -e POSTGRES_USER=ragadmin -e POSTGRES_PASSWORD=*** -e POSTGRES_DB=knowledge_rag -p 5432:5432 pgvector/pgvector:pg16 >nul 2>&1
if %errorlevel% neq 0 (
    docker start rag-pg >nul 2>&1
    echo   PostgreSQL 已启动
) else (
    echo   PostgreSQL 首次启动，等待就绪...
    :wait_pg
    timeout /t 3 /nobreak >nul
    docker exec rag-pg pg_isready -U ragadmin >nul 2>&1
    if %errorlevel% neq 0 goto wait_pg
    echo   PostgreSQL 就绪
)

echo [2/4] 初始化数据库...
docker cp "%~dp0scripts\init_db.sql" rag-pg:/init_db.sql >nul 2>&1
docker exec -i rag-pg psql -U ragadmin -d knowledge_rag -f /init_db.sql >nul 2>&1
echo   数据库初始化完成

echo [3/4] 安装依赖...
"%~dp0.venv\Scripts\pip.exe" install python-multipart -q >nul 2>&1

echo [4/4] 启动服务...
echo.
echo ========================================
echo   服务已启动！
echo   后端 API:  http://127.0.0.1:8000
echo   API 文档:  http://127.0.0.1:8000/docs
echo   健康检查:  http://127.0.0.1:8000/api/health
echo ========================================
echo   按 Ctrl+C 停止
echo.
cd /d "%~dp0"
"%~dp0.venv\Scripts\python.exe" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
pause
