@echo off
:: ============================================================
:: RIS — Gestionare Serviciu Windows
:: Comenzi rapide: start / stop / restart / status / logs
:: ============================================================
set SERVICE_NAME=RIS-Backend
set PROJECT_DIR=%~dp0
set PROJECT_DIR=%PROJECT_DIR:~0,-1%

:: Daca e dat argument direct (sc start/stop/restart/status)
if "%1"=="start"   goto do_start
if "%1"=="stop"    goto do_stop
if "%1"=="restart" goto do_restart
if "%1"=="status"  goto do_status
if "%1"=="logs"    goto do_logs

:: Meniu interactiv
echo.
echo  RIS — Gestionare Serviciu
echo  =========================
echo  1. Start
echo  2. Stop
echo  3. Restart
echo  4. Status
echo  5. Logs (ultimele 50 linii)
echo  6. Deschide UI in browser
echo  0. Iesire
echo.
set /p choice=Alegere:

if "%choice%"=="1" goto do_start
if "%choice%"=="2" goto do_stop
if "%choice%"=="3" goto do_restart
if "%choice%"=="4" goto do_status
if "%choice%"=="5" goto do_logs
if "%choice%"=="6" goto do_open
if "%choice%"=="0" exit /b 0
goto do_status

:do_start
echo Pornire %SERVICE_NAME%...
sc start %SERVICE_NAME%
timeout /t 2 /nobreak >nul
goto do_status

:do_stop
echo Oprire %SERVICE_NAME%...
sc stop %SERVICE_NAME%
goto end

:do_restart
echo Restart %SERVICE_NAME%...
sc stop %SERVICE_NAME%
timeout /t 3 /nobreak >nul
sc start %SERVICE_NAME%
timeout /t 2 /nobreak >nul
goto do_status

:do_status
echo.
sc query %SERVICE_NAME%
echo.
goto end

:do_logs
echo.
echo [stdout - ultimele 50 linii]
powershell -Command "Get-Content '%PROJECT_DIR%\logs\ris_service_stdout.log' -Tail 50 -ErrorAction SilentlyContinue"
echo.
echo [stderr - ultimele 20 linii]
powershell -Command "Get-Content '%PROJECT_DIR%\logs\ris_service_stderr.log' -Tail 20 -ErrorAction SilentlyContinue"
goto end

:do_open
start http://localhost:8001
goto end

:end
pause
