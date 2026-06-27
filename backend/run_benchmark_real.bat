@echo off
chcp 65001 >nul
cd /d %~dp0

echo ================================================================
echo  LynxMask Desktop -- Benchmark REAL (dokumenty z telefonu)
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
echo === Uruchamiam benchmark na realnych dokumentach ===
echo Folder: ..\Pliki testowe
echo Raporty: benchmark_results\real\
echo.
python benchmark_real.py

echo.
echo ================================================================
echo  Gotowe. Raporty w: benchmark_results\real\
echo ================================================================
pause
