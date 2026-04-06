@echo off
setlocal EnableDelayedExpansion
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"
title RIS — Tailscale Mode

echo.
echo  ================================================
echo   Roland Intelligence System — TAILSCALE MODE
echo  ================================================
echo.

:: .env fallback
if not exist ".env" (
    if exist ".env.example" copy ".env.example" ".env" >nul
)

:: Python deps fallback
python -c "import fastapi, aiosqlite, langgraph, fpdf, docx, httpx" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [1/4] Instalare dependinte Python...
    pip install -r requirements.txt -q
)

:: node_modules fallback
if not exist "frontend\node_modules" (
    echo  [1/4] Instalare dependinte npm...
    cd frontend && call npm install --silent >nul 2>&1 && cd ..
)

:: Directoare
if not exist "data" mkdir data
if not exist "outputs" mkdir outputs
if not exist "logs" mkdir logs
if not exist "backups" mkdir backups

:: Build frontend
echo  [2/4] Build frontend (PWA)...
cd frontend
call npm run build 2>&1
if %errorlevel% neq 0 (
    echo  [EROARE] Build frontend esuat!
    pause
    exit /b 1
)
cd ..
echo  [2/4] Build OK — dist/ generat.

:: Opreste TOATE instantele Python RIS (pythonw, uvicorn workers, reloaders)
echo  [3/4] Pornire backend pe 0.0.0.0:8001...
taskkill /f /t /im pythonw.exe >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /c:":8001 "') do (
    if not "%%p"=="0" taskkill /f /t /pid %%p >nul 2>&1
)
ping -n 4 127.0.0.1 >nul

:: Porneste backend cu uvicorn direct --no-reload (stabil, fara procese zombie)
start "RIS-Backend" /min cmd /c "cd /d "%PROJECT_DIR%" && uvicorn backend.main:app --host 0.0.0.0 --port 8001 > logs\ris_tailscale.log 2>&1"

:: Health check backend (max 15 sec)
echo  [3/4] Astept backend...
set "BACKEND_OK=0"
for /L %%i in (1,1,15) do (
    if "!BACKEND_OK!"=="0" (
        curl -s http://127.0.0.1:8001/api/health >nul 2>&1
        if !errorlevel! equ 0 (
            set "BACKEND_OK=1"
        ) else (
            ping -n 2 127.0.0.1 >nul
        )
    )
)

if "!BACKEND_OK!"=="0" (
    echo  [EROARE] Backend nu a pornit in 15 secunde. Verifica logs\ris_tailscale.log
    pause
    exit /b 1
)

:: Detecteaza IP Tailscale
echo  [4/4] Detectare IP Tailscale...
set "TAILSCALE_IP="
for /f "tokens=*" %%i in ('tailscale ip -4 2^>nul') do set "TAILSCALE_IP=%%i"

echo.
echo  ================================================
echo   RIS PORNIT — TAILSCALE MODE
echo  ================================================
echo.
echo   Local:      http://localhost:8001
if defined TAILSCALE_IP (
    echo   Tailscale:  http://!TAILSCALE_IP!:8001
    echo   PWA Phone:  http://!TAILSCALE_IP!:8001  ^(adauga la Home Screen^)
) else (
    echo   Tailscale:  [IP negasit — verifica ca Tailscale e conectat]
    echo   Comanda:    tailscale ip -4
)
echo.
echo   API Docs:   http://localhost:8001/docs
echo   Oprire:     inchide aceasta fereastra
echo  ================================================
echo.

:: Deschide browser local
if defined TAILSCALE_IP (
    start http://!TAILSCALE_IP!:8001
) else (
    start http://localhost:8001
)

echo  Apasa orice tasta pentru a opri RIS...
pause >nul

:: Oprire
taskkill /f /fi "WINDOWTITLE eq RIS-Backend*" >nul 2>&1
echo  RIS oprit.
