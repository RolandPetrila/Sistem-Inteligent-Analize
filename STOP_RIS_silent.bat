@echo off
:: Opreste backend (uvicorn/python pe port 8001)
for /f "tokens=5" %%p in ('netstat -aon ^| findstr ":8001.*LISTENING"') do (
    taskkill /pid %%p /f >nul 2>&1
)

:: Opreste frontend (vite/node pe port 5173)
for /f "tokens=5" %%p in ('netstat -aon ^| findstr ":5173.*LISTENING"') do (
    taskkill /pid %%p /f >nul 2>&1
)
