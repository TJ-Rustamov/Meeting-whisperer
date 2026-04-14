# Troubleshooting Guide - Meeting Whisperer Windows App Build

## Common Issues and Solutions

### Build Issues

#### 1. "Python is not installed or not in PATH"

**Problem**: The build script cannot find Python

**Solutions**:
```bash
# Check if Python is installed
python --version

# Add Python to PATH:
# 1. Open System Properties > Environment Variables
# 2. Edit PATH and add: C:\Python311 (or your Python version)
# 3. Restart command prompt

# Or use full path:
C:\Python311\python.exe -m pip install pyinstaller
```

#### 2. "Node.js is not installed"

**Problem**: npm or bun not found

**Solutions**:
```bash
# Check Node.js installation
node --version
npm --version

# Install from: https://nodejs.org/
# Or install bun: https://bun.sh/

# If using bun, install npm as well:
npm install -g npm
```

#### 3. PyInstaller build fails

**Problem**: `pyinstaller: command not found` or module errors

**Solutions**:
```bash
# Install/upgrade PyInstaller
pip install --upgrade pyinstaller

# Clear cache
cd launcher
pyinstaller --clean app_launcher.spec

# Check for hidden imports
pyinstaller app_launcher.spec --debug imports

# Manually add hidden imports to spec file if needed
# Edit app_launcher.spec and add to hiddenimports list
```

#### 4. Frontend build fails

**Problem**: `npm run build` returns errors

**Solutions**:
```bash
# Clear cache and reinstall
cd frontend
del /s /q node_modules
npm install
npm run build

# Check for build errors
npm run lint

# If using Bun:
bun clean
bun install
bun run build
```

#### 5. "FFmpeg not found"

**Problem**: Audio processing fails due to missing FFmpeg

**Solutions**:
```bash
# Install FFmpeg (Windows)
choco install ffmpeg

# Or download manually:
# https://ffmpeg.org/download.html
# Add to PATH

# Verify installation
ffmpeg -version
```

#### 6. Out of memory during build

**Problem**: Build process crashes with memory error

**Solutions**:
```bash
# Increase available memory
SET PYTHONUNBUFFERED=1

# Reduce build size by removing unused models
# Edit models/ directory to keep only needed models

# Build without all models first:
# 1. Remove large models temporarily
# 2. Build and test
# 3. Add models back
```

#### 7. Port already in use

**Problem**: "Address already in use" error when running app

**Solutions**:
```bash
# Find process using port
# Windows cmd:
netstat -ano | findstr :8000
netstat -ano | findstr :5173

# Kill process
taskkill /PID <process_id> /F

# Or use different ports in app_launcher.py:
BACKEND_PORT = 8001
FRONTEND_PORT = 5174
```

---

### Runtime Issues

#### 1. App crashes on start

**Problem**: Executable starts and immediately closes

**Solutions**:
```bash
# Run from command line to see error:
python launcher/app_launcher.py

# Or run exe with console:
# 1. Modify app_launcher.spec - change console=False to True
# 2. Rebuild with pyinstaller
```

#### 2. "Cannot find module" errors

**Problem**: App starts but backend crashes immediately

**Solutions**:
```bash
# Verify all dependencies installed
pip install -r backend/requirements.txt --upgrade

# Check Python version (3.9+ required)
python --version

# Verify torch installation (problematic on some systems)
python -c "import torch; print(torch.__version__)"

# If torch fails, reinstall:
pip install --upgrade torch torchaudio --index-url https://download.pytorch.org/whl/cpu
```

#### 3. Database locked error

**Problem**: "database is locked" when running multiple instances

**Solutions**:
```bash
# Close all instances

# Delete database to start fresh:
# Windows: Delete %APPDATA%\MeetingWhisperer\Meeting Whisperer\data\meetings.db

# Or modify connection string in app_launcher.py:
# Add timeout parameter:
'DATABASE_URL': f'sqlite:///{db_path}?timeout=10'
```

#### 4. Frontend won't load (blank page)

**Problem**: Browser opens but shows blank page

**Solutions**:
```bash
# Check if frontend built correctly
# Verify dist/ folder exists: frontend/dist/

# If not built, build manually:
cd frontend
npm run build

# Check console for errors:
# 1. Open browser developer console (F12)
# 2. Check Network tab for failed requests
# 3. Check Console tab for errors

# Common issue: API base URL incorrect
# Edit frontend/.env or vite.config.ts:
VITE_API_BASE_URL=http://localhost:8000
```

#### 5. Audio recording doesn't work

**Problem**: Mic input not working or no audio captured

**Solutions**:
```bash
# Check system audio permissions (Windows)
# 1. Settings > Privacy & Security > Microphone
# 2. Allow the app

# Verify FFmpeg installation
ffmpeg -version

# Check sample rate in app_launcher.py:
'WS_SAMPLE_RATE': '16000'

# Test with different sample rates if needed
```

#### 6. Transcription is slow

**Problem**: API call takes long time

**Solutions**:
```bash
# Check device configuration in app_launcher.py:
'WHISPER_DEVICE': 'cpu'  # Change to: 'cuda' for GPU

# Adjust compute type for faster processing:
'WHISPER_COMPUTE_TYPE': 'int8'  # Use int8 for faster but less accurate

# Reduce beam size for faster transcription:
'WHISPER_BEAM_SIZE': '1'  # Lower values = faster
```

---

### Installation Issues

#### 1. Installer fails with permission error

**Problem**: "Access denied" when installing

**Solutions**:
```bash
# Run installer as Administrator
# Right-click installer > Run as administrator

# Or from command line:
runas /user:Administrator "path\to\installer.exe"
```

#### 2. Cannot uninstall previously installed version

**Problem**: Uninstall fails or leaves files behind

**Solutions**:
```bash
# Manual cleanup:
# 1. Stop all MeetingWhisperer processes
# 2. Delete: C:\Program Files\MeetingWhisperer\
# 3. Delete: %APPDATA%\MeetingWhisperer\ (if you want fresh start)
# 4. Remove from Start Menu if shortcut remains
```

#### 3. Installer says wrong version already installed

**Problem**: Cannot upgrade due to version mismatch

**Solutions**:
```bash
# Method 1: Use "Uninstall" in Settings > Apps
# Method 2: Manual uninstall (see above)
# Method 3: Manually edit version in installer.iss before building
```

---

### Model Issues

#### 1. Models fail to download

**Problem**: "Cannot download model" errors

**Solutions**:
```bash
# Check internet connection
ping huggingface.co

# Models should be bundled in app
# If not found, ensure models/ directory is included:
# launcher/app_launcher.spec should have:
# (str(project_root / 'models'), 'models'),

# Manually download model:
python -c "from faster_whisper import WhisperModel; WhisperModel.from_pretrained('base.en')"

# Move to models/faster-whisper-base.en/
```

#### 2. Wrong model loaded

**Problem**: App loads incorrect model or old version

**Solutions**:
```bash
# Clear model cache:
# Delete: %USERPROFILE%\.cache\huggingface\

# Specify model path explicitly in app_launcher.py:
'WHISPER_MODEL_PATH': 'models/faster-whisper-base.en'

# Rebuild and test
```

---

### Performance Issues

#### 1. High memory usage

**Problem**: App uses 2+ GB RAM

**Solutions**:
```bash
# Reduce model size in app_launcher.py:
# Use 'tiny' or 'base' instead of 'large'

# Reduce batch size:
# Edit backend configuration

# Monitor memory:
tasklist | findstr python
Get-Process python | Select-Object WorkingSet
```

#### 2. CPU usage very high

**Problem**: CPU constantly at 100%

**Solutions**:
```bash
# Check if transcription is running
# Use Task Manager to see which process

# Reduce beam size for faster processing:
'WHISPER_BEAM_SIZE': '1'

# Use quantized model:
'WHISPER_COMPUTE_TYPE': 'int8'
```

#### 3. Slow file operations

**Problem**: Saving/loading recordings is slow

**Solutions**:
```bash
# Use SSD for AppData if possible
# Move data directory to faster storage

# Edit app_launcher.py:
self.data_dir = Path('D:/fast_storage/MeetingWhisperer')

# Check disk space:
wmic logicaldisk get name,size,freespace

# Clean up old audio files:
# Delete: %APPDATA%\MeetingWhisperer\Meeting Whisperer\data\audio\*.wav
```

---

### Network Issues

#### 1. Cannot communicate with backend

**Problem**: "Failed to connect to http://localhost:8000"

**Solutions**:
```bash
# Verify backend is running:
netstat -ano | findstr :8000

# Try direct connection:
curl http://localhost:8000/health

# Check firewall:
# Windows Defender Firewall > Allow app through firewall
# Add python.exe or MeetingWhisperer.exe

# Reset to default port
```

#### 2. CORS errors in console

**Problem**: "Cross-Origin Request Blocked" in browser console

**Solutions**:
```bash
# Verify CORS settings in app_launcher.py:
'CORS_ORIGINS': 'http://localhost:5173,http://127.0.0.1:5173'

# If ports changed, update this accordingly:
env.update({
    ...,
    'CORS_ORIGINS': f'http://localhost:{FRONTEND_PORT}',
})

# Rebuild and test
```

---

### Debugging

#### Enable Debug Logging

```bash
# Run with debug mode (Windows)
python launcher/app_launcher.py --dev > debug.log 2>&1

# Search for errors:
findstr /i "error" debug.log
```

#### Check Application Logs

```bash
# Application directories:
# Data: %APPDATA%\MeetingWhisperer\Meeting Whisperer\data\
# Logs: Check database and any .log files
```

#### Use Task Manager

```
# Monitor processes:
# 1. Open Task Manager (Ctrl+Shift+Esc)
# 2. View Details tab
# 3. Find python.exe processes
# 4. Check CPU, Memory, Network usage
```

---

### Getting Help

If you encounter issues not listed above:

1. **Collect information**:
   ```bash
   python --version
   node --version
   pip list | findstr fastapi uvicorn torch
   ```

2. **Run with debugging**:
   ```bash
   python launcher/app_launcher.py 2>&1 | tee debug.log
   ```

3. **Check project issues**:
   Visit the GitHub repository and search existing issues

4. **Provide details**:
   - Windows version (`winver`)
   - Python version
   - Full error message
   - Steps to reproduce
   - Debug logs

---

### Quick Reset

If everything is broken, clean restart:

```bash
# Stop all processes
taskkill /F /IM python.exe
taskkill /F /IM MeetingWhisperer.exe

# Clear caches
cd frontend && del /s /q node_modules && npm install
rm -r launcher/build launcher/dist

# Clean rebuild
cd launcher
pyinstaller --clean app_launcher.spec
```

---

Last updated: 2024
