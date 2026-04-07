@echo off
:: ============================================================
:: RIS — Setup Windows Service via NSSM
:: Roland Intelligence System — Serviciu Windows automat
:: Rulare: Click dreapta → "Run as Administrator"
:: ============================================================
setlocal EnableDelayedExpansion

set SERVICE_NAME=RIS-Backend
set PROJECT_DIR=%~dp0
set PROJECT_DIR=%PROJECT_DIR:~0,-1%
set NSSM=%PROJECT_DIR%\tools\nssm.exe
set PYTHON_CMD=python
set BACKEND_CMD=-m backend.main
set LOG_DIR=%PROJECT_DIR%\logs

echo.
echo  RIS — Roland Intelligence System
echo  Setup Windows Service
echo  ================================
echo.

:: ── Verifica drepturi administrator ────────────────────────
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [EROARE] Rulati scriptul ca Administrator!
    echo          Click dreapta pe fisier → "Run as administrator"
    echo.
    pause
    exit /b 1
)

:: ── Verifica Python ─────────────────────────────────────────
%PYTHON_CMD% --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [EROARE] Python nu este instalat sau nu e in PATH!
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('where python') do set PYTHON_PATH=%%i
echo [OK] Python gasit: %PYTHON_PATH%

:: ── Descarca NSSM daca lipseste ─────────────────────────────
if not exist "%NSSM%" (
    echo [INFO] nssm.exe nu exista in tools\ — descarcare automata...
    echo.

    if not exist "%PROJECT_DIR%\tools" mkdir "%PROJECT_DIR%\tools"

    :: Incearca cu PowerShell (Windows 10+)
    powershell -Command "& {$url='https://nssm.cc/ci/nssm-2.24-101-g897c7ad.zip'; $zip='%TEMP%\nssm.zip'; $out='%TEMP%\nssm_extract'; Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing; Expand-Archive -Path $zip -DestinationPath $out -Force; $nssm=Get-ChildItem -Path $out -Name 'nssm.exe' -Recurse | Where-Object {$_ -like '*win64*'} | Select-Object -First 1; if(!$nssm){$nssm=Get-ChildItem -Path $out -Name 'nssm.exe' -Recurse | Select-Object -First 1} Copy-Item (Join-Path $out $nssm) '%NSSM%' -Force}"

    if not exist "%NSSM%" (
        echo [EROARE] Nu s-a putut descarca nssm.exe automat.
        echo          Descarcati manual de la: https://nssm.cc/download
        echo          si copiati nssm.exe in: %PROJECT_DIR%\tools\
        echo.
        pause
        exit /b 1
    )
    echo [OK] nssm.exe descarcat cu succes in tools\
)

echo [OK] NSSM gasit: %NSSM%

:: ── Verifica daca serviciul exista deja ─────────────────────
sc query %SERVICE_NAME% >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo [INFO] Serviciul %SERVICE_NAME% exista deja.
    echo        Actualizare configuratie...
    "%NSSM%" stop %SERVICE_NAME% >nul 2>&1
    timeout /t 2 /nobreak >nul
)

:: ── Creeaza / actualizeaza serviciul ────────────────────────
echo.
echo [INFO] Configurare serviciu %SERVICE_NAME%...

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: Instaleaza serviciul
"%NSSM%" install %SERVICE_NAME% "%PYTHON_PATH%" %BACKEND_CMD%

:: Configurare
"%NSSM%" set %SERVICE_NAME% AppDirectory "%PROJECT_DIR%"
"%NSSM%" set %SERVICE_NAME% DisplayName "RIS Backend — Roland Intelligence System"
"%NSSM%" set %SERVICE_NAME% Description "Backend FastAPI pentru Roland Intelligence System. Ofera API REST si serveste frontend-ul PWA."
"%NSSM%" set %SERVICE_NAME% Start SERVICE_AUTO_START
"%NSSM%" set %SERVICE_NAME% AppEnvironmentExtra "RIS_ENV=production"

:: Logging NSSM
"%NSSM%" set %SERVICE_NAME% AppStdout "%LOG_DIR%\ris_service_stdout.log"
"%NSSM%" set %SERVICE_NAME% AppStderr "%LOG_DIR%\ris_service_stderr.log"
"%NSSM%" set %SERVICE_NAME% AppStdoutCreationDisposition 4
"%NSSM%" set %SERVICE_NAME% AppStderrCreationDisposition 4
"%NSSM%" set %SERVICE_NAME% AppRotateFiles 1
"%NSSM%" set %SERVICE_NAME% AppRotateBytes 5242880

:: Restart la crash
"%NSSM%" set %SERVICE_NAME% AppRestartDelay 3000
"%NSSM%" set %SERVICE_NAME% AppThrottle 30000

echo [OK] Serviciu configurat.

:: ── Porneste serviciul ───────────────────────────────────────
echo.
echo [INFO] Pornire serviciu...
"%NSSM%" start %SERVICE_NAME%
timeout /t 3 /nobreak >nul

sc query %SERVICE_NAME% | find "RUNNING" >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo  ================================================
    echo  [OK] Serviciu RIS-Backend PORNIT cu succes!
    echo.
    echo  Acces local:    http://localhost:8001
    echo  Acces Tailscale: http://[IP-Tailscale]:8001
    echo  Gaseste IP:     tailscale ip -4
    echo.
    echo  Comenzi rapide:
    echo    sc start RIS-Backend
    echo    sc stop RIS-Backend
    echo    sc query RIS-Backend
    echo  ================================================
) else (
    echo [ATENTIE] Serviciul nu e inca RUNNING — verifica logs\ris_service_stderr.log
    sc query %SERVICE_NAME%
)

echo.
pause
