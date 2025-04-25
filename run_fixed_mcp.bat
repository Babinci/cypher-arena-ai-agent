@echo off

REM Set default directories
set PROJECT_DIR=C:\Users\walko\IT_projects\Cypher_arena_ai_agent\mcp_server
set VENV_DIR=C:\Users\walko\IT_projects\Cypher_arena_ai_agent\.venv

REM Set working directory
cd %PROJECT_DIR%


%VENV_DIR%\Scripts\python.exe -u %PROJECT_DIR%\\main.py 