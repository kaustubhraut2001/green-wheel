@echo off
setlocal enabledelayedexpansion

echo.
echo ============================================================
echo   WalletPro — Full Stack Startup Script
echo ============================================================
echo.

REM ── Step 1: Check Docker ─────────────────────────────────────────────────
echo [1/5] Checking Docker Desktop...
docker info > nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Docker Desktop is not running!
    echo  Please start Docker Desktop and wait for it to fully load,
    echo  then run this script again.
    echo.
    pause
    exit /b 1
)
echo        Docker is running.

REM ── Step 2: Check Node.js ────────────────────────────────────────────────
echo.
echo [2/5] Checking Node.js...
node --version > nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Node.js is not installed or not in PATH!
    echo  Please install Node.js from https://nodejs.org (LTS version)
    echo  then run this script again.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('node --version') do set NODE_VER=%%v
echo        Node.js %NODE_VER% found.

REM ── Step 3: Build frontend locally ───────────────────────────────────────
echo.
echo [3/5] Installing frontend dependencies...
cd /d "%~dp0frontend"

if not exist node_modules (
    echo        Running npm install (first time, may take a few minutes)...
    npm install --legacy-peer-deps
    if %errorlevel% neq 0 (
        echo.
        echo  ERROR: npm install failed!
        echo  Try running manually: cd frontend ^&^& npm install --legacy-peer-deps
        pause
        exit /b 1
    )
) else (
    echo        node_modules already exists, skipping install.
    echo        (Delete frontend\node_modules to force reinstall)
)

echo.
echo [4/5] Building frontend (Vite)...
npm run build
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Frontend build failed!
    echo  Try running manually: cd frontend ^&^& npm run build
    pause
    exit /b 1
)
echo        Frontend built successfully into frontend\dist\

REM ── Step 4: Start Docker services ────────────────────────────────────────
echo.
echo [5/5] Starting all Docker services...
cd /d "%~dp0"

REM Stop existing containers cleanly
docker compose down --remove-orphans 2>nul

REM Start everything
docker compose up --build -d
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: docker compose up failed!
    echo  Check the error above. Common fixes:
    echo    - If postgres unhealthy: run reset.bat first
    echo    - If port in use: check nothing else is on 3000/8000/5432/6379
    pause
    exit /b 1
)

REM ── Done ─────────────────────────────────────────────────────────────────
echo.
echo ============================================================
echo   All services are starting up!
echo ============================================================
echo.
echo   Frontend UI  : http://localhost:3000
echo   Backend API  : http://localhost:8000
echo   Swagger Docs : http://localhost:8000/docs
echo   Celery Flower: http://localhost:5555
echo.
echo   Watch logs   : docker compose logs -f
echo   Stop all     : docker compose down
echo ============================================================
echo.
echo Waiting 10 seconds for services to initialise...
timeout /t 10 /nobreak > nul
echo.
echo Opening browser...
start http://localhost:3000
pause
