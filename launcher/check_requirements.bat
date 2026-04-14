@echo off
REM Pre-build checklist for Meeting Whisperer
REM Verifies all requirements are installed before building

echo.
echo ========================================
echo Meeting Whisperer - Pre-Build Checklist
echo ========================================
echo.

setlocal enabledelayedexpansion

set CHECKS_PASSED=0
set CHECKS_FAILED=0

REM Function to check tool
setlocal enabledelayedexpansion

REM Check Python
echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   ✗ Python not found
    set /a CHECKS_FAILED+=1
) else (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo   ✓ !PYTHON_VERSION!
    set /a CHECKS_PASSED+=1
)

REM Check Node.js
echo Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo   ✗ Node.js not found
    set /a CHECKS_FAILED+=1
) else (
    for /f "tokens=*" %%i in ('node --version 2^>^&1') do set NODE_VERSION=%%i
    echo   ✓ Node.js !NODE_VERSION!
    set /a CHECKS_PASSED+=1
)

REM Check npm
echo Checking npm...
npm --version >nul 2>&1
if errorlevel 1 (
    echo   ✗ npm not found
    set /a CHECKS_FAILED+=1
) else (
    for /f "tokens=*" %%i in ('npm --version 2^>^&1') do set NPM_VERSION=%%i
    echo   ✓ npm !NPM_VERSION!
    set /a CHECKS_PASSED+=1
)

REM Check Git
echo Checking Git...
git --version >nul 2>&1
if errorlevel 1 (
    echo   ✗ Git not found (optional)
    set /a CHECKS_FAILED+=1
) else (
    for /f "tokens=*" %%i in ('git --version 2^>^&1') do set GIT_VERSION=%%i
    echo   ✓ !GIT_VERSION!
    set /a CHECKS_PASSED+=1
)

REM Check FFmpeg
echo Checking FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo   ✗ FFmpeg not found
    set /a CHECKS_FAILED+=1
) else (
    for /f "tokens=1" %%i in ('ffmpeg -version 2^>^&1 ^| findstr /i ffmpeg') do set FFMPEG_VERSION=%%i
    echo   ✓ FFmpeg found
    set /a CHECKS_PASSED+=1
)

REM Check PyInstaller
echo Checking PyInstaller...
pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo   ✗ PyInstaller not installed
    set PYINSTALLER_MISSING=1
    set /a CHECKS_FAILED+=1
) else (
    for /f "tokens=*" %%i in ('pyinstaller --version 2^>^&1') do set PYINSTALLER_VERSION=%%i
    echo   ✓ PyInstaller !PYINSTALLER_VERSION!
    set /a CHECKS_PASSED+=1
)

REM Check Inno Setup
echo Checking Inno Setup...
for /f "delims=" %%i in ('where iscc.exe 2^>nul') do set ISCC_PATH=%%i
if "%ISCC_PATH%"=="" (
    echo   - Inno Setup not found (optional - installer creation disabled)
) else (
    echo   ✓ Inno Setup found
    set /a CHECKS_PASSED+=1
)

REM Check disk space
echo.
echo Checking disk space...
for /f "tokens=3" %%i in ('wmic logicaldisk get name^,freespace ^| findstr /i c:') do set FREESPACE=%%i

if defined FREESPACE (
    set /a FREESPACEGB=!FREESPACE!/1024/1024/1024
    if !FREESPACEGB! geq 20 (
        echo   ✓ !FREESPACEGB! GB free (plenty)
        set /a CHECKS_PASSED+=1
    ) else if !FREESPACEGB! geq 10 (
        echo   ⚠ !FREESPACEGB! GB free (minimal, may need more)
    ) else (
        echo   ✗ !FREESPACEGB! GB free (too little, need at least 20 GB)
        set /a CHECKS_FAILED+=1
    )
)

REM Check Python packages
echo.
echo Checking Python packages...
python -c "import torch" >nul 2>&1
if errorlevel 1 (
    echo   ⚠ PyTorch not installed (will be installed during build)
) else (
    echo   ✓ PyTorch found
)

python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo   ⚠ FastAPI not installed (will be installed during build)
) else (
    echo   ✓ FastAPI found
)

REM Summary
echo.
echo ========================================
echo Summary
echo ========================================
echo Checks passed:  %CHECKS_PASSED%
echo Checks failed:  %CHECKS_FAILED%
echo.

if %CHECKS_FAILED% geq 2 (
    echo ✗ CRITICAL: Missing required dependencies!
    echo.
    echo Please install the missing tools. See INSTALLATION_GUIDE.md for details.
    echo.
    pause
    exit /b 1
) else if %CHECKS_FAILED% equ 1 (
    echo ⚠ WARNING: Some dependencies missing
    echo.
    echo Review the issues above. See INSTALLATION_GUIDE.md for details.
    echo.
    set /p CONTINUE="Continue anyway? (Y/N): "
    if /i not "!CONTINUE!"=="Y" exit /b 1
) else (
    echo ✓ All required dependencies are installed!
    echo.
    echo You can now run:
    echo   - build.bat (full build with all steps)
    echo   - quickbuild.bat (faster rebuild if already built once)
    echo.
)

pause
exit /b 0
