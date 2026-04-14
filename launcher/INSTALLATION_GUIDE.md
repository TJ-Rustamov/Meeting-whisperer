# Installation and Setup Guide

Complete guide for setting up the Meeting Whisperer Windows Application build environment.

## Table of Contents
1. [System Requirements](#system-requirements)
2. [Step-by-Step Installation](#step-by-step-installation)
3. [Verification](#verification)
4. [Building the App](#building-the-app)
5. [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements
- **OS**: Windows 10 Build 1909 or later
- **RAM**: 8 GB (16 GB recommended for ML models)
- **Disk**: 20 GB free space (for models and dependencies)
- **CPU**: Any modern processor (recommend i5 or better)

### Development Requirements (for building)
- **Python**: 3.9, 3.10, 3.11, or 3.12
- **Node.js**: 18.0 or later
- **Git**: For version control

### Optional
- **GPU**: NVIDIA GPU with CUDA support (for faster transcription)
- **Visual Studio Build Tools**: Some packages require C++ compiler (Windows only)

## Step-by-Step Installation

### Step 1: Install Visual Studio Build Tools

Some Python packages require a C++ compiler. Install Visual Studio Build Tools:

1. Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. Run installer
3. Select "Desktop development with C++"
4. Install and restart

Alternatively, install Visual Studio Community with C++ support.

### Step 2: Install Python

**Option A: From Python.org (Recommended)**

1. Download Python 3.11 from: https://www.python.org/downloads/
2. Run installer
3. **Important**: Check "Add Python to PATH"
4. Choose "Install Now" or "Customize installation"
5. Complete installation

**Option B: From Microsoft Store**

```powershell
# Search for "Python 3.11" in Microsoft Store
# Click "Get" to install
```

**Option C: Using Chocolatey**

```powershell
choco install python
```

**Verify Installation**:

```bash
python --version
# Should output: Python 3.11.x or similar

python -m pip --version
# Should output: pip x.x.x
```

### Step 3: Install Node.js and npm

**Option A: From nodejs.org (Recommended)**

1. Download LTS version from: https://nodejs.org/
2. Run installer
3. Accept defaults
4. Complete installation

**Option B: Using Chocolatey**

```powershell
choco install nodejs
```

**Option C: Using nvm (Advanced)**

```powershell
# Install nvm for Windows
# Then: nvm install 20.0.0
```

**Verify Installation**:

```bash
node --version
# Should output: v18.x.x or later

npm --version
# Should output: 9.x.x or later
```

### Step 4: Install Git

**Option A: From git-scm.com**

1. Download from: https://git-scm.com/download/win
2. Run installer
3. Accept defaults or customize
4. Complete installation

**Option B: Using Chocolatey**

```powershell
choco install git
```

**Verify Installation**:

```bash
git --version
# Should output: git version x.x.x
```

### Step 5: Install FFmpeg

FFmpeg is required for audio processing.

**Option A: Using Chocolatey (Easiest)**

```powershell
choco install ffmpeg
```

**Option B: Download Binary**

1. Download from: https://ffmpeg.org/download.html
2. Extract to: `C:\ffmpeg`
3. Add to PATH:
   - Open System Properties → Environment Variables
   - Add `C:\ffmpeg\bin` to PATH
   - Restart command prompt

**Option C: Using Scoop**

```powershell
scoop install ffmpeg
```

**Verify Installation**:

```bash
ffmpeg -version
# Should show FFmpeg version info
```

### Step 6: Install PyInstaller Requirements

```bash
# Open Command Prompt and run:
pip install --upgrade pip setuptools wheel

# Install build tools
pip install pyinstaller psutil
```

### Step 7: Optional - Install Inno Setup (for creating installer)

For creating the professional Windows installer:

1. Download from: https://jrsoftware.org/isdl.php
2. Run installer
3. Complete installation at default location
4. Verify: `"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"` exists

## Verification

### Test Python Environment

```bash
python -c "import sys; print(sys.version)"
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
```

### Test Node.js Environment

```bash
npm list -g
npm list npm
```

### Test Required Tools

```bash
pyinstaller --version
ffmpeg -version
git --version
```

### Test Project Dependencies

```bash
cd backend
pip install -r requirements.txt
# Wait for completion...

cd ../frontend
npm install
# Wait for completion...
```

## Building the App

Now that everything is installed, build the application:

### Quick Build (Recommended)

```bash
cd launcher
quickbuild.bat
```

This will:
1. Install all dependencies
2. Build the React frontend
3. Create the standalone executable
4. Build the Windows installer (if Inno Setup installed)

### Monitor Build Progress

The build process will show:
- ✓ Python dependencies installed
- ✓ Node.js dependencies installed
- ✓ Frontend built successfully
- ✓ Executable created
- ✓ Installer created (if applicable)

### Verify Build Output

Check these locations for successful build:

```
launcher/dist/MeetingWhisperer/MeetingWhisperer.exe
  ↑ The portable executable

launcher/output/MeetingWhisperer-Setup-1.0.0.exe
  ↑ The Windows installer (if Inno Setup installed)
```

## Testing the Build

### Test Portable Executable

```bash
# Run the built executable
launcher\dist\MeetingWhisperer\MeetingWhisperer.exe

# Should:
# 1. Start a backend server on port 8000
# 2. Start a frontend server on port 5173
# 3. Open browser to http://localhost:5173
# 4. Show working meeting whisperer interface
```

### Test Installer

```bash
# Run the installer
launcher\output\MeetingWhisperer-Setup-1.0.0.exe

# Should:
# 1. Show Windows installer wizard
# 2. Allow choosing installation location
# 3. Create Start Menu shortcuts
# 4. Allow launch at end of installation
```

## Environment Variables

Optional - Set custom values before building:

```bash
# Windows Command Prompt
set WHISPER_MODEL=large
set WHISPER_DEVICE=cuda
set BACKEND_PORT=8001

# Or in PowerShell
$env:WHISPER_MODEL = "large"
$env:WHISPER_DEVICE = "cuda"
$env:BACKEND_PORT = "8001"
```

## Directory Structure After Installation

```
d:\live transcript\
├── backend/                          # Backend FastAPI code
│   ├── app/                         # Application code
│   ├── requirements.txt             # Python dependencies
│   └── Dockerfile
├── frontend/                        # Frontend React code
│   ├── src/                        # Source code
│   ├── dist/                       # Built output (created by npm run build)
│   ├── node_modules/               # Dependencies (created by npm install)
│   ├── package.json
│   └── vite.config.ts
├── launcher/                        # Launcher and build scripts
│   ├── app_launcher.py             # Main launcher script
│   ├── build.bat                   # Full build script
│   ├── quickbuild.bat              # Quick build script
│   ├── app_launcher.spec           # PyInstaller config
│   ├── installer.iss               # Inno Setup config
│   ├── dist/                       # Build output (created by build)
│   ├── output/                     # Final installer (created by build)
│   ├── README.md
│   └── TROUBLESHOOTING.md
└── models/                          # ML models (bundled with app)
    └── faster-whisper-base.en/
```

## Common Installation Issues

### Python version conflict

```bash
# If multiple Python versions installed:
# Use specific version
C:\Python311\python.exe --version

# Update pip for specific version
C:\Python311\python.exe -m pip install --upgrade pip
```

### Path issues on Windows

```bash
# Check current PATH
echo %PATH%

# Permanently add to PATH:
# 1. Search "Environment Variables"
# 2. Click "Edit the system environment variables"
# 3. Click "Environment Variables..."
# 4. Under "User variables", click "New"
# 5. Variable name: PATH
# 6. Variable value: C:\Users\YourUsername\AppData\Local\Programs\Python\Python311\Scripts;C:\Users\YourUsername\AppData\Local\Programs\Python\Python311
# 7. Click OK and restart terminal
```

### npm install fails

```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules
cd frontend
rmdir /s /q node_modules

# Reinstall
npm install --verbose

# If still fails, try auth:
npm login
npm install
```

### PyInstaller fails

```bash
# Upgrade
pip install --upgrade pyinstaller

# Clear cache
cd launcher
rm -r build dist *.pyc

# Try again
pyinstaller --clean app_launcher.spec
```

## GPU Support (Optional)

To use NVIDIA GPU for faster transcription:

### 1. Install CUDA Toolkit

Download from: https://developer.nvidia.com/cuda-toolkit

```bash
# Verify CUDA installation
nvcc --version
```

### 2. Install cuDNN

Download from: https://developer.nvidia.com/cudnn

### 3. Install PyTorch with GPU support

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### 4. Update app_launcher.py

```python
env.update({
    'WHISPER_DEVICE': 'cuda',  # Changed from 'cpu'
    'WHISPER_COMPUTE_TYPE': 'float16',  # Recommended for GPU
})
```

### 5. Rebuild

```bash
cd launcher
pyinstaller --clean app_launcher.spec
```

## Next Steps

1. ✓ Complete all installation steps
2. ✓ Run `quickbuild.bat` to build the app
3. ✓ Test the executable
4. ✓ Deploy to users

## Support

- See [README.md](README.md) for build details
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for issue resolution
- Check GitHub issues for common problems

---

Last updated: 2024
Installation time: ~30-45 minutes (including downloads)
Build time: ~15-30 minutes (depending on system specs)
