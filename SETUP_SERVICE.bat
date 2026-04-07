@echo off
:: RIS -- Setup Windows Service
:: Click dreapta -> Run as administrator

cd /d "%~dp0"
python tools\setup_service.py
pause
