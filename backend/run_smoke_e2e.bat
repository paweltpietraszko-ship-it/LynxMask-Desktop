@echo off
chcp 65001 >nul
cd /d %~dp0

echo ================================================================
echo  LynxMask Desktop -- Smoke E2E (pliki testowe)
echo  %date% %time%
echo ================================================================

echo.
echo === Sprawdzam backend ===
curl -s http://127.0.0.1:8765/health >nul 2>&1
if %errorlevel% neq 0 (
    echo UWAGA: Backend nie odpowiada na 127.0.0.1:8765
    echo Uruchom pseudominizer_api.py i odpal ten skrypt ponownie.
    pause
    exit /b 1
)
echo Backend dziala.

echo.
echo === Uruchamiam smoke E2E ===
echo Raport zostanie zapisany w: benchmark_results\smoke\
echo.
python -m pytest tests/test_smoke_e2e.py -v -s

echo.
echo ================================================================
echo  Gotowe. Raport: benchmark_results\smoke\smoke_e2e_report.txt
echo ================================================================
pause
