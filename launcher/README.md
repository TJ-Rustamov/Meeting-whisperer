# Meeting Whisperer - Windows Application Builder

This directory contains scripts and configuration to build a complete Windows installer for Meeting Whisperer.

## Overview

The build process creates:
1. **Portable EXE** - Standalone executable that can run from any location
2. **Windows Installer** - Professional MSI/EXE installer for easy installation and uninstallation

The final app includes:
- Full Python runtime (embedded with PyInstaller)
- FastAPI backend server
- React/Vite frontend
- All ML models (faster-whisper, pyannote)
- Database management (SQLite stored in user's AppData)
- Auto-start capabilities
- System tray integration (optional)

## Prerequisites

Before building, ensure you have:

### 1. Python 3.9+
```bash
# Check version
python --version

# Download from: https://www.python.org/downloads/
```

### 2. Node.js / npm / bun
```bash
# Check version
node --version
npm --version

# Download from: https://nodejs.org/
# Or install bun: https://bun.sh/
```

### 3. Git
```bash
# Verify
git --version
```

### 4. Inno Setup (for installer creation - optional)
```
Download from: https://jrsoftware.org/isdl.php
```

### 5. FFmpeg (for audio processing)
```bash
# Windows with Chocolatey
choco install ffmpeg

# Or download from: https://ffmpeg.org/download.html
```

## Build Instructions

### Quick Start (Automated)

The easiest way to build is using the provided batch script:

```bash
cd launcher
build.bat
```

This will:
1. Install all dependencies
2. Build the React frontend
3. Create the standalone executable
4. Generate the Windows installer

### Manual Build Process

If you prefer more control or encounter issues:

#### Step 1: Install Dependencies

```bash
# Install backend dependencies
cd backend
pip install -r requirements.txt

# Install build tools
cd ../launcher
pip install -r requirements-build.txt

# Install frontend dependencies
cd ../frontend
npm install
# OR: bun install
```

#### Step 2: Build Frontend

```bash
cd frontend
npm run build
# Output will be in: frontend/dist
```

#### Step 3: Create Executable

```bash
cd launcher

# Verify app_launcher.spec exists
# Then run PyInstaller
pyinstaller --clean app_launcher.spec --distpath dist --buildpath build

# Output will be in: dist/MeetingWhisperer/MeetingWhisperer.exe
```

#### Step 4: Create Installer

```bash
# Install Inno Setup from: https://jrsoftware.org/isdl.php
# Then run:
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss

# Output will be in: output/MeetingWhisperer-Setup-*.exe
```

## Directory Structure

```
launcher/
├── app_launcher.py          # Main application launcher (entry point)
├── app_launcher.spec        # PyInstaller configuration
├── installer.iss            # Inno Setup installer configuration
├── build.bat                # Automated build script
├── dev_server.py            # Development server helper
├── requirements-build.txt   # Build dependencies
├── dist/                    # Output: Built executable (generated)
├── build/                   # PyInstaller build temp (generated)
├── output/                  # Output: Windows installer (generated)
└── assets/                  # Icons and assets (create if needed)
    └── app.ico              # Application icon (optional)
```

## File Descriptions

### app_launcher.py
**Purpose**: Main entry point that runs when users launch the app

**Key Functions**:
- Detects or uses embedded Python
- Starts FastAPI backend server on port 8000
- Serves frontend on port 5173
- Opens app in default browser
- Manages process lifecycle
- Handles graceful shutdown

**Configuration**:
- Backend port: 8000
- Frontend port: 5173
- Database location: `%APPDATA%\MeetingWhisperer\Meeting Whisperer\data\`
- Models location: Bundled with exe

### app_launcher.spec
**Purpose**: PyInstaller configuration file

**Key Options**:
- `console=False` - No console window shown
- `datas` - Includes backend code, frontend build, models
- `hiddenimports` - Explicit imports for PyInstaller
- `excludedimports` - Reduces executable size

### installer.iss
**Purpose**: Inno Setup configuration for Windows installer

**Features**:
- Creates Start Menu shortcuts
- Optional desktop icon
- Optional startup task
- Firewall exception (admin required)
- Clean uninstall
- 64-bit support

## Configuration & Environment Variables

The app uses these environment variables (all set automatically):

```
APP_NAME=Meeting Whisperer
DATABASE_URL=sqlite:///[AppData]/meetings.db
DATA_DIR=[AppData]/data
AUDIO_DIR=[AppData]/data/audio
WHISPER_MODEL_PATH=[App]/models/faster-whisper-base.en
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

To modify, edit the environment dict in `app_launcher.py`:

```python
env.update({
    'WHISPER_DEVICE': 'cpu',  # Change to 'cuda' for GPU
    'WHISPER_COMPUTE_TYPE': 'int8',  # Options: int8, float16, float32
    # ... other variables
})
```

## Customization

### Change Application Icon

1. Prepare a 256x256 PNG image
2. Convert to ICO format using an online converter
3. Place at: `launcher/assets/app.ico`
4. Rebuild with PyInstaller

### Change Branding

Edit these in `app_launcher.py`:
```python
APP_NAME = "Meeting Whisperer"
ORG_NAME = "MeetingWhisperer"
```

And in `installer.iss`:
```
#define MyAppName "Meeting Whisperer"
#define MyAppPublisher "Meeting Whisperer"
```

### Bundled Models

Models are included in the build automatically from `models/` directory.

To update models:
1. Replace model files in `models/` directory
2. Rebuild the application

### Ports

To use different ports, edit in `app_launcher.py`:
```python
BACKEND_PORT = 8000
FRONTEND_PORT = 5173
```

And update CORS settings accordingly.

## Testing

### Test the Standalone Executable

```bash
# Navigate to built executable
cd launcher/dist/MeetingWhisperer

# Run it
MeetingWhisperer.exe

# Or with flags
MeetingWhisperer.exe --dev --no-browser
```

### Available Flags

```
--dev              Run in development mode (auto-reload backend)
--no-browser       Don't open browser automatically
```

### Test the Installer

1. Run the generated installer from `launcher/output/`
2. Follow installation wizard
3. Launch from Start Menu or Desktop shortcut
4. Verify functionality

## Troubleshooting

### Build Issues

**PyInstaller fails to find modules**
```bash
# Clear cache
pyinstaller --clean app_launcher.spec
```

**Frontend build fails**
```bash
# Clear node_modules and reinstall
cd frontend
rm -r node_modules
npm install
npm run build
```

**Missing FFmpeg**
```bash
# Windows with Chocolatey
choco install ffmpeg

# Or add to PATH manually
```

### Runtime Issues

**Port already in use**
```python
# Change ports in app_launcher.py
BACKEND_PORT = 8001
FRONTEND_PORT = 5174
```

**Database errors**
```bash
# Delete app data to start fresh
rmdir %APPDATA%\MeetingWhisperer /s /q
```

**Backend/Frontend won't start**
```bash
# Run with console visible for debugging
python app_launcher.py
```

## Distribution

### Package for Distribution

```bash
# Portable version (zip the dist folder)
cd launcher\dist
powershell Compress-Archive -Path MeetingWhisperer -DestinationPath ..\output\MeetingWhisperer-Portable.zip

# Or create installer executable (see above)
```

### Sign Installer (Optional)

```bash
# Requires code signing certificate
signtool sign /f cert.pfx /p password /tr http://timestamp.server /td sha256 installer.exe
```

## Performance Optimization

For faster builds:

1. **Skip models** - Remove unused models from `models/` directory
2. **Use UPX** - Compress executable (enables automatically if installed)
3. **Change compute type** - Use `int8` instead of `float32` for smaller models
4. **Reduce included packages** - Remove unnecessary imports

## Advanced Configuration

### GPU Support

Edit `app_launcher.py` to enable CUDA:

```python
env.update({
    'WHISPER_DEVICE': 'cuda',
    'WHISPER_COMPUTE_TYPE': 'float16',  # Recommended for GPU
})
```

### Custom Database Location

The database is automatically stored in user's AppData. To change:

```python
# In AppConfig class
self.db_path = Path('C:/custom/path/meetings.db')
```

### Multiple Instances

Allow multiple app instances:

```python
# In ProcessManager class, remove port availability check
# Or use different ports for each instance
```

## Support & Maintenance

For issues or updates:
1. Check GitHub issues
2. Review application logs (stored with database)
3. Collect debug info: `app_launcher.py --dev > debug.log 2>&1`

## Building for Different Architectures

Currently configured for 64-bit Windows (x86_64).

To build for 32-bit:
1. Edit `installer.iss` - Change `ArchitecturesAllowed` to `x86`
2. Ensure Python 32-bit installation
3. Rebuild PyInstaller spec

## Version Updates

When updating:

1. Update version in `app_launcher.py`
2. Update `#define MyAppVersion` in `installer.iss`
3. Rebuild everything
4. Distribute new installer

Users keep their database when upgrading (stored in AppData).

## Next Steps

1. Install all prerequisites
2. Run `build.bat` from launcher directory
3. Test the generated executable
4. Distribute the installer to users

Good luck! 🎉
