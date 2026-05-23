@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo ByAldon DailyWall - Windows EXE builder
echo ============================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo Python launcher "py" was not found.
    echo Install Python for Windows first, then run this file again.
    pause
    exit /b 1
)

echo Installing/updating build tools...
py -m pip install --upgrade pip
py -m pip install -r requirements.txt pyinstaller
if errorlevel 1 (
    echo.
    echo Could not install the required Python packages.
    pause
    exit /b 1
)

echo.
echo Cleaning old build folders...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo Building EXE...
py -m PyInstaller "ByAldon DailyWall.spec" --clean --noconfirm
if errorlevel 1 (
    echo.
    echo Build failed.
    pause
    exit /b 1
)

echo.
echo Done.
echo Your EXE is here:
echo %cd%\dist\ByAldon DailyWall.exe
echo.
echo Test this EXE in your VM by copying ONLY the EXE file.
echo It should create its own config in:
echo %%APPDATA%%\ByAldon DailyWall\config.json
echo.
pause
