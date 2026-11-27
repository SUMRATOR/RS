@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ================================================
echo RS - RUBIK STUDIO
echo Сборка автономной Windows-версии
echo ================================================

py -3.13 -m PyInstaller ^
 --noconfirm ^
 --clean ^
 --onedir ^
 --name RUBIK_STUDIO ^
 --icon "rubik_studio\assets\rubik_studio.ico" ^
 --collect-all nicegui ^
 --collect-all webview ^
 --collect-all sqlalchemy ^
 --collect-all aiosqlite ^
 --collect-all passlib ^
 --collect-all bcrypt ^
 _rubik_exe_launcher_F.py

echo.
echo Сборка завершена.
pause
