@echo off
REM Quick build script for Meeting Whisperer
REM Builds frontend, executable, and installer in sequence

setlocal enabledelayedexpansion

set PROJECT_ROOT=%~dp0..
set LAUNCHER_DIR=%PROJECT_ROOT%\launcher
set FRONTEND_DIR=%PROJECT_ROOT%\frontend

cd /d "%LAUNCHER_DIR%"

echo.
echo ================================================
echo Meeting Whisperer - Quick Build
echo ================================================
echo.

REM Step 1: Build frontend
echo [1/3] Building frontend...
cd /d "%FRONTEND_DIR%"
call npm run build
if errorlevel 1 (
    echo ERROR: Frontend build failed
    pause
    exit /b 1
)
echo ✓ Frontend built
echo.

REM Step 2: PyInstaller
echo [2/3] Creating executable...
cd /d "%LAUNCHER_DIR%"
pyinstaller --clean app_launcher.spec --distpath dist --buildpath build
if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)
echo ✓ Executable created
echo.

REM Step 3: Create installer (optional)
echo [3/3] Creating installer...
set ISCC_PATH=
for /f "delims=" %%i in ('where iscc.exe 2^>nul') do set ISCC_PATH=%%i

if "%ISCC_PATH%"=="" (
    echo ⚠ Inno Setup not found (optional)
    echo Install from: https://jrsoftware.org/isdl.php
) else (
    echo Found Inno Setup at: %ISCC_PATH%
    "%ISCC_PATH%" installer.iss
    if errorlevel 1 (
        echo WARNING: Installer creation had issues
    ) else (
        echo ✓ Installer created
    )
)

echo.
echo ================================================
echo ✓ Build completed!
echo ================================================
echo.
echo Output locations:
if exist "dist\MeetingWhisperer\MeetingWhisperer.exe" (
    echo   Executable: %LAUNCHER_DIR%\dist\MeetingWhisperer\MeetingWhisperer.exe
)
echo.
echo Test the app:
echo   "%LAUNCHER_DIR%\dist\MeetingWhisperer\MeetingWhisperer.exe"
echo.
pause
