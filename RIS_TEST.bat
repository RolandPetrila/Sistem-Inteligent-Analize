@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: RIS Test Runner — Ruleaza toate testele si salveaza rezultatele
:: Dublu-click pentru executie. Rezultatele se salveaza in TEST_RESULTS.log

cd /d "%~dp0"

set LOGFILE=TEST_RESULTS.log
set TIMESTAMP=%date:~6,4%-%date:~3,2%-%date:~0,2% %time:~0,2%:%time:~3,2%:%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%

echo.
echo ========================================
echo   RIS Test Runner
echo   %TIMESTAMP%
echo ========================================
echo.

:: Header in log
echo. >> %LOGFILE%
echo ============================================================ >> %LOGFILE%
echo TEST RUN: %TIMESTAMP% >> %LOGFILE%
echo ============================================================ >> %LOGFILE%

:: --- PYTEST ---
echo [1/2] Running pytest...
echo. >> %LOGFILE%
echo --- PYTEST (backend) --- >> %LOGFILE%

python -m pytest tests/ -v --tb=short 2>&1 | tee -a %LOGFILE% 2>nul
if !errorlevel! equ 0 (
    set PYTEST_RESULT=PASS
) else (
    set PYTEST_RESULT=FAIL
)

:: Fallback daca tee nu exista (Windows fara Git bash in PATH)
if not exist "%LOGFILE%" (
    python -m pytest tests/ -v --tb=short >> %LOGFILE% 2>&1
)

echo PYTEST: !PYTEST_RESULT! >> %LOGFILE%
echo.
echo   PYTEST: !PYTEST_RESULT!
echo.

:: --- VITEST ---
echo [2/2] Running vitest...
echo. >> %LOGFILE%
echo --- VITEST (frontend) --- >> %LOGFILE%

cd frontend
call npx vitest run 2>&1 | tee -a ..\%LOGFILE% 2>nul
if !errorlevel! equ 0 (
    set VITEST_RESULT=PASS
) else (
    set VITEST_RESULT=FAIL
)
cd ..

echo VITEST: !VITEST_RESULT! >> %LOGFILE%
echo.
echo   VITEST: !VITEST_RESULT!
echo.

:: --- SUMMARY ---
echo ---------------------------------------- >> %LOGFILE%
echo SUMMARY: pytest=!PYTEST_RESULT! vitest=!VITEST_RESULT! >> %LOGFILE%
echo ============================================================ >> %LOGFILE%

echo ========================================
echo   REZULTAT: pytest=!PYTEST_RESULT! vitest=!VITEST_RESULT!
echo   Salvat in: %LOGFILE%
echo ========================================
echo.

if "!PYTEST_RESULT!"=="FAIL" (
    echo   [!] Teste pytest PICAT — vezi detalii in %LOGFILE%
)
if "!VITEST_RESULT!"=="FAIL" (
    echo   [!] Teste vitest PICAT — vezi detalii in %LOGFILE%
)

echo.
echo Apasa orice tasta pentru a inchide...
pause >nul
