@echo off
REM build.bat — LynxMask Desktop (Windows)
REM Buduje release: frontend (npm) + Tauri (cargo).

setlocal
set SCRIPT_DIR=%~dp0
set FRONTEND_DIR=%SCRIPT_DIR%frontend

echo === LynxMask Desktop — Build ===
echo.

REM 1. Zależności JS
echo [1/3] npm install...
cd /d "%FRONTEND_DIR%"
call npm install --silent
if errorlevel 1 ( echo BLAD: npm install && exit /b 1 )

REM 2. TypeScript + Vite
echo [2/3] npm run build...
call npm run build
if errorlevel 1 ( echo BLAD: npm run build && exit /b 1 )

REM 3. Tauri release
echo [3/3] cargo tauri build...
call npm run tauri build
if errorlevel 1 ( echo BLAD: tauri build && exit /b 1 )

echo.
echo Build gotowy.
echo Instalator: frontend\src-tauri\target\release\bundle\
