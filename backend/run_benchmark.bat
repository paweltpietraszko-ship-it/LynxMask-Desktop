@echo off
cd /d %~dp0
echo.
echo ============================================================
echo  LynxMask — Benchmark
echo ============================================================
echo.

REM Zatrzymaj stary backend jeśli działa (po PID portu 8765)
echo [1/3] Zatrzymuję stary backend...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8765 " ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 2 /nobreak >nul

REM Uruchom świeży backend — nowy token zapisze się do api_token.txt
echo [2/3] Uruchamiam backend (nowy token)...
start "LynxMask Backend" cmd /c "python pseudominizer_api.py > backend.log 2>&1"

REM Czekaj aż backend wystartuje i zapisze token
echo      Czekam na start backendu...
timeout /t 6 /nobreak >nul

REM Sprawdź czy backend odpowiada
curl -s http://127.0.0.1:8765/health >nul 2>&1
if errorlevel 1 (
    echo [BŁĄD] Backend nie odpowiedział po 6 sekundach.
    echo        Sprawdź backend.log
    pause
    exit /b 1
)

echo [3/3] Backend gotowy. Uruchamiam benchmark...
echo.
python benchmark.py --count 50
echo.
pause
