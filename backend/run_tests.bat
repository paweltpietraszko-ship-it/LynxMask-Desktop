@echo off
chcp 65001 >nul
cd /d %~dp0

echo ================================================================
echo  LynxMask Desktop -- pelny zestaw testow
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

:: Folder na raport (jeden wspolny z benchmarkami)
for /f "tokens=1-3 delims=/-. " %%a in ("%date%") do set D=%%c%%b%%a
for /f "tokens=1-2 delims=:." %%a in ("%time: =0%") do set T=%%a%%b
set REPORT_DIR=benchmark_results\testy\run_%D%_%T%
mkdir %REPORT_DIR% 2>nul
set LOG=%REPORT_DIR%\wyniki.txt

echo LynxMask Desktop -- testy %date% %time% > %LOG%
echo ================================================================ >> %LOG%

echo.
echo === [1/3] Testy pytest (unit + HTTP z backendem) ===
echo Trwa... (wyniki w %LOG%)
echo. >> %LOG%
echo === [1/3] Testy pytest (unit + HTTP z backendem) === >> %LOG%
python -m pytest tests/test_pseudominizer.py -v --tb=short >> %LOG% 2>&1
set PYTEST_EXIT=%errorlevel%

echo.
echo === [2/3] Testy pipeline HTTP (test_pipeline.py) ===
echo Trwa...
echo. >> %LOG%
echo === [2/3] Testy pipeline HTTP (test_pipeline.py) === >> %LOG%
python tests\test_pipeline.py >> %LOG% 2>&1

echo.
echo === [3/3] Testy adversarialne (bezposredni import) ===
echo Trwa...
echo. >> %LOG%
echo === [3/3] Testy adversarialne (bezposredni import) === >> %LOG%
python -m pytest tests\test_anonymizer_adversarial.py -v --tb=short >> %LOG% 2>&1
python -m pytest tests\test_output_guard_adversarial.py -v --tb=short >> %LOG% 2>&1
python -m pytest tests\test_pipeline_adversarial.py -v --tb=short >> %LOG% 2>&1
python -m pytest tests\test_pipeline_v2.py -v --tb=short >> %LOG% 2>&1

echo. >> %LOG%
echo ================================================================ >> %LOG%
echo Gotowe. pytest exit code: %PYTEST_EXIT% >> %LOG%
echo ================================================================ >> %LOG%

echo.
echo ================================================================
echo  Gotowe. pytest exit code: %PYTEST_EXIT%
echo  Raport: %REPORT_DIR%\wyniki.txt
echo ================================================================
pause
