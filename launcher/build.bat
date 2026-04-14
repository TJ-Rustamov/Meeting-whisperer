@echo off
REM Build script for Meeting Whisperer Windows Application
REM This script builds the frontend, creates the PyInstaller executable, and generates the installer

setlocal enabledelayedexpansion

set PROJECT_ROOT=%~dp0..
set LAUNCHER_DIR=%PROJECT_ROOT%\launcher
set BACKEND_DIR=%PROJECT_ROOT%\backend
set FRONTEND_DIR=%PROJECT_ROOT%\frontend
set BUILD_DIR=%LAUNCHER_DIR%\dist
set OUTPUT_DIR=%LAUNCHER_DIR%\output

echo.
echo ========================================
echo Meeting Whisperer - Windows App Builder
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9+ from python.org
    pause
    exit /b 1
)

echo ✓ Python found
python --version

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js from nodejs.org
    pause
    exit /b 1
)

echo ✓ Node.js found
node --version

REM Step 1: Install/Update dependencies
echo.
echo [Step 1/5] Installing Python dependencies...
cd /d "%BACKEND_DIR%"
pip install -r requirements.txt --upgrade
if errorlevel 1 (
    echo ERROR: Failed to install backend dependencies
    pause
    exit /b 1
)
echo ✓ Backend dependencies installed

cd /d "%LAUNCHER_DIR%"
pip install pyinstaller psutil inno-setup-variables
if errorlevel 1 (
    echo WARNING: Failed to install launcher dependencies
)
echo ✓ Launcher dependencies installed

REM Step 2: Build frontend
echo.
echo [Step 2/5] Building frontend...
cd /d "%FRONTEND_DIR%"

REM Check if node_modules exists
if not exist "node_modules" (
    echo Installing frontend dependencies...
    call bun install
    if errorlevel 1 (
        echo WARNING: bun install failed, trying npm
        call npm install
    )
)

REM Build frontend
if exist "vite.config.ts" (
    call npm run build
    if errorlevel 1 (
        echo ERROR: Frontend build failed
        pause
        exit /b 1
    )
    echo ✓ Frontend built successfully
) else (
    echo ERROR: vite.config.ts not found
    pause
    exit /b 1
)

REM Step 3: Prepare build directory
echo.
echo [Step 3/5] Preparing build directory...
if exist "%BUILD_DIR%" (
    echo Cleaning old build...
    rmdir /s /q "%BUILD_DIR%"
)
mkdir "%BUILD_DIR%"
echo ✓ Build directory prepared

REM Step 4: Create PyInstaller executable
echo.
echo [Step 4/5] Creating PyInstaller executable...
cd /d "%LAUNCHER_DIR%"

REM Check if spec file exists
if not exist "app_launcher.spec" (
    echo ERROR: app_launcher.spec not found
    pause
    exit /b 1
)

REM Build with PyInstaller
pyinstaller --clean app_launcher.spec --distpath "%BUILD_DIR%" --buildpath "%LAUNCHER_DIR%\build"
if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)
echo ✓ Executable created

REM Step 5: Create installer
echo.
echo [Step 5/5] Creating Windows installer...

REM Check if Inno Setup is installed
for /f "delims=" %%i in ('where iscc.exe 2^>nul') do set ISCC_PATH=%%i

if "%ISCC_PATH%"=="" (
    echo WARNING: Inno Setup is not installed
    echo Please install Inno Setup from: https://jrsoftware.org/isdl.php
    echo Then run this script again to create the installer
    echo.
    echo Current executable location: %BUILD_DIR%\MeetingWhisperer\MeetingWhisperer.exe
    echo.
    pause
    exit /b 0
) else (
    echo Found Inno Setup: %ISCC_PATH%
    "%ISCC_PATH%" "%LAUNCHER_DIR%\installer.iss"
    if errorlevel 1 (
        echo ERROR: Installer creation failed
        pause
        exit /b 1
    )
    echo ✓ Installer created
)

REM Summary
echo.
echo ========================================
echo ✓ Build completed successfully!
echo ========================================
echo.
echo Output locations:
if exist "%BUILD_DIR%\MeetingWhisperer\MeetingWhisperer.exe" (
    echo   Portable app: %BUILD_DIR%\MeetingWhisperer\MeetingWhisperer.exe
)
if exist "%LAUNCHER_DIR%\output\MeetingWhisperer-Setup*.exe" (
    echo   Installer: %LAUNCHER_DIR%\output\MeetingWhisperer-Setup-*.exe
)
echo.
echo Next steps:
echo 1. Test the executable: %BUILD_DIR%\MeetingWhisperer\MeetingWhisperer.exe
echo 2. Distribute the installer from the output folder
echo.
pause
