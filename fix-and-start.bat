@echo off
echo ============================================================
echo  Docker Hub Connectivity Fix for Windows
echo ============================================================
echo.

echo [1/4] Checking Docker is running...
docker info > nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker Desktop is not running. Please start it first.
    pause
    exit /b 1
)
echo       Docker is running.

echo.
echo [2/4] Pulling base images individually (this diagnoses network issues)...
echo       Pulling postgres:16-alpine ...
docker pull postgres:16-alpine
if %errorlevel% neq 0 goto :network_fix

echo       Pulling redis:7-alpine ...
docker pull redis:7-alpine

echo       Pulling python:3.12-slim ...
docker pull python:3.12-slim
if %errorlevel% neq 0 goto :network_fix

echo       Pulling node:20-alpine ...
docker pull node:20-alpine

echo       Pulling nginx:alpine ...
docker pull nginx:alpine

echo.
echo [3/4] All images pulled successfully!
echo.
echo [4/4] Cleaning old containers and volumes, then starting fresh...
docker compose down --remove-orphans -v
docker compose up --build -d

echo.
echo ============================================================
echo  All services started!
echo  Frontend  : http://localhost:3000
echo  Backend   : http://localhost:8000
echo  Swagger   : http://localhost:8000/docs
echo  Flower    : http://localhost:5555
echo ============================================================
echo.
echo Watch logs: docker compose logs -f
pause
exit /b 0

:network_fix
echo.
echo ============================================================
echo  NETWORK FIX NEEDED
echo ============================================================
echo  Docker cannot reach Docker Hub. Try these steps:
echo.
echo  OPTION A - Restart Docker Desktop:
echo    1. Right-click Docker Desktop tray icon
echo    2. Click "Restart"
echo    3. Wait 30 seconds, then run this script again
echo.
echo  OPTION B - Fix DNS in Docker Desktop:
echo    1. Open Docker Desktop
echo    2. Go to Settings ^> Docker Engine
echo    3. Add this to the JSON:
echo       "dns": ["8.8.8.8", "8.8.4.4"]
echo    4. Click "Apply ^& Restart"
echo    5. Run this script again
echo.
echo  OPTION C - Use a VPN or different network
echo    (Corporate networks sometimes block Docker Hub)
echo.
pause
exit /b 1
