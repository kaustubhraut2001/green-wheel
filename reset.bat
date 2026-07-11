@echo off
echo ============================================================
echo  WalletPro — Full Reset (wipes DB, rebuilds everything)
echo ============================================================
echo.
echo WARNING: This will DELETE all database data and restart fresh.
echo Press Ctrl+C to cancel, or any key to continue...
pause > nul

echo.
echo [1/3] Stopping and removing all containers + volumes...
cd /d "%~dp0"
docker compose down --remove-orphans -v
echo        Done.

echo.
echo [2/3] Building frontend locally...
cd /d "%~dp0frontend"
if exist node_modules (
    npm run build
) else (
    npm install --legacy-peer-deps && npm run build
)
cd /d "%~dp0"

echo.
echo [3/3] Starting all services fresh...
docker compose up --build -d

echo.
echo ============================================================
echo  Reset complete! Fresh start with empty database.
echo  Frontend : http://localhost:3000
echo  Backend  : http://localhost:8000
echo  Swagger  : http://localhost:8000/docs
echo ============================================================
pause
