@echo off
:: RIS -- Gestionare serviciu Windows (start/stop/restart/status/logs)
cd /d "%~dp0"
set WINSW=tools\RIS-Backend.exe

if "%1"=="start"   goto do_start
if "%1"=="stop"    goto do_stop
if "%1"=="restart" goto do_restart
if "%1"=="status"  goto do_status
if "%1"=="logs"    goto do_logs

echo.
echo  RIS -- Gestionare Serviciu
echo  ===========================
echo  1. Start
echo  2. Stop
echo  3. Restart
echo  4. Status
echo  5. Logs (ultimele 50 linii)
echo  6. Deschide browser la localhost:8001
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
echo Pornire RIS-Backend...
%WINSW% start
timeout /t 2 /nobreak >nul
goto do_status

:do_stop
echo Oprire RIS-Backend...
%WINSW% stop
goto end

:do_restart
echo Restart RIS-Backend...
%WINSW% restart
timeout /t 2 /nobreak >nul
goto do_status

:do_status
echo.
sc query RIS-Backend
echo.
goto end

:do_logs
echo.
echo [stdout - ultimele 50 linii]
powershell -NoProfile -Command "Get-Content 'logs\ris_service_stdout.log' -Tail 50 -ErrorAction SilentlyContinue"
echo.
echo [stderr - ultimele 20 linii]
powershell -NoProfile -Command "Get-Content 'logs\ris_service_stderr.log' -Tail 20 -ErrorAction SilentlyContinue"
goto end

:do_open
start http://localhost:8001
goto end

:end
pause
