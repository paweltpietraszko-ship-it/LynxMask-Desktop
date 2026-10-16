@echo off
chcp 65001 >nul
cd /d %~dp0

echo.
echo ============================================================
echo  LynxMask — podglad maskowania (realne dokumenty)
echo  Bez ground_truth — tylko raport do odczytu
echo ============================================================
echo.

curl -s http://127.0.0.1:8765/health >nul 2>&1
if %errorlevel% neq 0 (
    echo Backend nie dziala. Uruchom: python pseudominizer_api.py
    pause
    exit /b 1
)

python preview_real_docs.py
echo.
pause
