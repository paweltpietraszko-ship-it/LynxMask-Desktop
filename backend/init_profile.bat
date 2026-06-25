@echo off
REM init_profile.bat — tworzy pusty profil pseudominizera
REM Uruchom raz po instalacji, przed pierwszym uruchomieniem

cd /d "%~dp0"

if not exist "anon_profiles\pseudominizer" (
    mkdir "anon_profiles\pseudominizer"
    echo Utworzono folder anon_profiles\pseudominizer
) else (
    echo Folder anon_profiles\pseudominizer juz istnieje
)

echo Gotowe. Mozesz uruchomic pseudominizer.
pause
