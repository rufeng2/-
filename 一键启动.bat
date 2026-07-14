@echo off
chcp 65001 >nul
title 企业知识库 RAG 系统

echo ========================================
echo   企业知识库 RAG 系统 - 一键启动
echo ========================================
echo.
echo 正在检查运行环境...
echo.

:: 检查 Docker
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo [!!] Docker Desktop 未运行
    echo     请先启动 Docker Desktop，然后重新运行本脚本
    echo.
    echo     或者手动启动后端（详见 SETUP.md）
    pause
    exit /b 1
)

:: 检查 PostgreSQL 容器
docker ps --filter "name=rag-pg" --format "{{.Names}}" | findstr "rag-pg" >nul
if %errorlevel% neq 0 (
    echo [1/3] 正在启动 PostgreSQL（首次会拉取镜像，约需几分钟）...
    docker run -d ^
        --name rag-pg ^
        -e POSTGRES_USER=ragadmin ^
        -e POSTGRES_PASSWORD=ragadmin123 ^
        -e POSTGRES_DB=knowledge_rag ^
        -p 5432:5432 ^
        pgvector/pgvector:pg16 >nul 2>&1

    if %errorlevel% neq 0 (
        echo [!!] PostgreSQL 启动失败
        echo     可能是镜像拉取超时，重试或见 SETUP.md
        pause
        exit /b 1
    )

    echo   等待数据库就绪...
    :wait_pg
    timeout /t 3 /nobreak >nul
    docker exec rag-pg pg_isready -U ragadmin >nul 2>&1
    if %errorlevel% neq 0 goto wait_pg
    echo   ✓ PostgreSQL 就绪
) else (
    echo [1/3] PostgreSQL 已在运行 ✓
)

:: 初始化数据库表
echo [2/3] 初始化数据库...
docker cp "%~dp0scripts\init_db.sql" rag-pg:/init_db.sql >nul 2>&1
docker exec -i rag-pg psql -U ragadmin -d knowledge_rag -f /init_db.sql >nul 2>&1
echo   ✓ 数据库初始化完成

:: 安装后端依赖并启动
echo [3/3] 启动后端服务...
echo.
echo ========================================
echo   服务地址
echo   后端 API:  http://127.0.0.1:8000
echo   API 文档:  http://127.0.0.1:8000/docs
echo   健康检查:  http://127.0.0.1:8000/api/health
echo ========================================
echo.

cd /d "%~dp0backend"

pip install -r requirements.txt -q 2>nul

set DATABASE_URL=postgresql+asyncpg://ragadmin:ragadmin123@localhost:5432/knowledge_rag
set DEEPSEEK_API_KEY=***
set DASHSCOPE_API_KEY=***
set LLM_MODEL=deepseek-chat

uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level info

pause
