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

echo.
echo === [1/3] Testy pytest (unit + HTTP z backendem) ===
python -m pytest tests/test_pseudominizer.py -v --tb=short
set PYTEST_EXIT=%errorlevel%

echo.
echo === [2/3] Testy pipeline HTTP (test_pipeline.py) ===
python tests\test_pipeline.py

echo.
echo === [3/3] Testy adversarialne (bezposredni import) ===
python -m pytest tests\test_anonymizer_adversarial.py -v --tb=short
python -m pytest tests\test_output_guard_adversarial.py -v --tb=short
python -m pytest tests\test_pipeline_adversarial.py -v --tb=short
python -m pytest tests\test_pipeline_v2.py -v --tb=short

echo.
echo ================================================================
echo  Gotowe. pytest exit code: %PYTEST_EXIT%
echo ================================================================
pause
