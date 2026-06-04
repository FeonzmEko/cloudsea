@echo off
title Cloudsea Forecast
cd /d "%~dp0"

echo.
echo   Cloudsea Forecast - starting...
echo.

REM 检查 .env
if not exist ".env" (
    echo   [!] .env not found. Copy .env.example to .env and fill API keys first.
    echo       copy .env.example .env
    pause
    exit /b 1
)

REM 检查 Python 依赖
python -c "import fastapi" 2>nul
if errorlevel 1 (
    echo   [*] Installing Python dependencies...
    pip install -r requirements.txt
    echo.
)

REM 检查前端是否已构建
if not exist "frontend\dist\index.html" (
    echo   [*] Building frontend...
    cd frontend
    if not exist "node_modules" (
        call npm install
    )
    call npm run build
    cd ..
    echo.
)

echo   [OK] Starting service: http://localhost:8000
echo   [i] Press Ctrl+C to stop.
echo.

start http://localhost:8000
python src/server.py
