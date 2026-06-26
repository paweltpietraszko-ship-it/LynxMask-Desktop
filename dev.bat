@echo off
REM dev.bat — LynxMask Desktop (Windows)
REM Uruchamia backend Python + Tauri dev (hot-reload).

setlocal
set SCRIPT_DIR=%~dp0
set FRONTEND_DIR=%SCRIPT_DIR%frontend
set BACKEND_DIR=%SCRIPT_DIR%backend

echo === LynxMask Desktop — Dev ===
echo.

REM 1. Backend Python w osobnym oknie
echo [1/3] Uruchamiam backend (port 8765)...
start "LynxMask Backend" /D "%BACKEND_DIR%" python pseudominizer_api.py

REM Poczekaj chwilę na start backendu
timeout /t 3 /nobreak > nul

REM 2. Zależności JS
echo [2/3] npm install...
cd /d "%FRONTEND_DIR%"
call npm install --silent
if errorlevel 1 ( echo BLAD: npm install && exit /b 1 )

REM 3. Tauri dev
echo [3/3] cargo tauri dev...
call npm run tauri dev
