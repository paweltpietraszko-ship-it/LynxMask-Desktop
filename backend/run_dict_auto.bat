@echo off
chcp 65001 >nul
cd /d %~dp0

echo.
echo ============================================================
echo  LynxMask — auto-slownik z benchmarku (bez recznej roboty)
echo ============================================================
echo.

python dict_auto_builder.py %*
echo.
pause
