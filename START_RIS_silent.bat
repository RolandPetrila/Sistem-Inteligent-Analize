@echo off
setlocal EnableDelayedExpansion
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

:: .env fallback
if not exist ".env" (
    if exist ".env.example" copy ".env.example" ".env" >nul
)

:: node_modules fallback
if not exist "frontend\node_modules" (
    cd frontend && call npm install --silent >nul 2>&1 && cd ..
)

:: Python deps fallback
python -c "import fastapi, aiosqlite, langgraph, fpdf, docx, httpx" >nul 2>&1
if %errorlevel% neq 0 (
    pip install -r requirements.txt -q >nul 2>&1
)

:: Directoare
if not exist "data" mkdir data
if not exist "outputs" mkdir outputs
if not exist "logs" mkdir logs
if not exist "backups" mkdir backups

:: Pornire backend — complet hidden (pythonw nu afiseaza consola)
start /b "" pythonw -m uvicorn backend.main:app --host 0.0.0.0 --port 8001 >nul 2>&1

:: Health check backend (max 10 sec)
set "BACKEND_OK=0"
for /L %%i in (1,1,10) do (
    if "!BACKEND_OK!"=="0" (
        curl -s http://127.0.0.1:8001/api/health >nul 2>&1
        if !errorlevel! equ 0 (
            set "BACKEND_OK=1"
        ) else (
            ping -n 2 127.0.0.1 >nul
        )
    )
)

:: Pornire frontend — hidden via node direct
start /b "" cmd /c "cd /d "%PROJECT_DIR%\frontend" && npx vite --port 5173" >nul 2>&1

:: Asteptam frontend-ul
ping -n 4 127.0.0.1 >nul

:: Deschidem browser-ul
start http://localhost:5173
