# Meeting Whisperer - Windows App Builder

**Transform your Meeting Whisperer project into a professional Windows application!**

This directory contains everything needed to build, test, and deploy a complete Windows installer for Meeting Whisperer.

## 🚀 Quick Start (5 minutes)

### Prerequisites Check
```bash
cd launcher
check_requirements.bat
```

### Build the App
```bash
cd launcher
quickbuild.bat
```

Done! Your app is ready in `launcher/dist/MeetingWhisperer/` and installer in `launcher/output/`

## 📋 What You'll Get

✅ **Complete Windows Application** including:
- Backend FastAPI server
- Frontend React/Vite interface  
- All ML models (faster-whisper)
- SQLite database
- System integration (shortcuts, uninstaller)

✅ **Two Distribution Formats**:
- **Professional Installer** (.exe) - For end users
- **Portable App** - For portable deployment

✅ **User Data Persistence**:
- Database stored in user's AppData
- Survives app updates
- Easy backup and restore

## 📚 Documentation

Choose your next step:

### 👤 **For Users**
- [Installation Guide](INSTALLATION_GUIDE.md) - Complete setup instructions
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions

### 🔨 **For Developers**
- [README.md](README.md) - Full build documentation
- [Build Scripts](#build-scripts) - Available build tools
- [Configuration](config.example.ini) - Customize settings

### 📦 **For Distribution**
- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Distribution strategies
- [Testing](#testing-checklist) - Verification steps

## 🛠️ Build Scripts

### `quickbuild.bat` (Recommended)
**Fast rebuild** - Use if you've built before
```bash
cd launcher
quickbuild.bat
```
Takes: ~5-10 minutes

### `build.bat`
**Full build** - Complete from scratch
```bash
cd launcher
build.bat
```
Takes: ~15-30 minutes
Includes: dependency installation, frontend build, executable creation, installer creation

### `check_requirements.bat`
**Verify prerequisites** - Run this first!
```bash
cd launcher
check_requirements.bat
```
Takes: ~1 minute
Checks: Python, Node.js, FFmpeg, PyInstaller, disk space

## 📁 File Structure

```
launcher/
├── 📜 app_launcher.py           ← Main entry point
├── 📋 app_launcher.spec         ← PyInstaller config
├── 📋 installer.iss             ← Inno Setup config
├── 🎯 build.bat                 ← Full build script
├── ⚡ quickbuild.bat            ← Fast rebuild
├── ✓ check_requirements.bat     ← Check prerequisites
├── 📖 README.md                 ← Full documentation
├── 📖 INSTALLATION_GUIDE.md     ← Setup instructions
├── 📖 TROUBLESHOOTING.md        ← Problem solving
├── 📖 DEPLOYMENT_GUIDE.md       ← Distribution guide
├── ⚙️ config.example.ini        ← Configuration template
├── 📦 requirements-build.txt    ← Build dependencies
├── dist/                        ← Output: Built executable (generated)
├── build/                       ← PyInstaller temp (generated)
└── output/                      ← Output: Windows installer (generated)
```

## 🔧 Prerequisites

Before building, ensure you have:

- [ ] **Python 3.9+** - [Download](https://www.python.org/downloads/)
- [ ] **Node.js 18+** - [Download](https://nodejs.org/)
- [ ] **Git** - [Download](https://git-scm.com/)
- [ ] **FFmpeg** - [Download](https://ffmpeg.org/) or `choco install ffmpeg`
- [ ] **Visual Studio Build Tools** - [Download](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
- [ ] **Inno Setup** (optional, for installer) - [Download](https://jrsoftware.org/isdl.php)

**Quick startup:** See [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) for step-by-step setup.

## 🏗️ Build Process

### Step 1️⃣: Check Prerequisites
```bash
check_requirements.bat
```

### Step 2️⃣: Install Dependencies
```bash
# Automatic with build.bat, or manual:
pip install -r requirements-build.txt
cd ..\frontend && npm install
```

### Step 3️⃣: Build Frontend
```bash
# Automatic with build scripts, or manual:
cd ..\frontend
npm run build
```

### Step 4️⃣: Create Executable
```bash
# Automatic with build scripts, or manual:
pyinstaller --clean app_launcher.spec
```

### Step 5️⃣: Create Installer
```bash
# Automatic with build.bat (if Inno Setup installed)
# Or run manually:
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

**Output files:**
- Portable app: `launcher/dist/MeetingWhisperer/MeetingWhisperer.exe`
- Installer: `launcher/output/MeetingWhisperer-Setup-1.0.0.exe`

## 🧪 Testing Checklist

After building, test these scenarios:

- [ ] Run standalone executable
- [ ] Backend starts on port 8000
- [ ] Frontend loads in browser (port 5173)
- [ ] Can record audio
- [ ] Transcription works
- [ ] Database saves and loads
- [ ] Run installer
- [ ] Launch from Start Menu
- [ ] Data persists after restart
- [ ] Uninstall is clean

## ⚙️ Configuration

### Runtime Environment Variables

Customize app behavior by setting before launching:

```bash
set WHISPER_DEVICE=cuda              # Use GPU (if available)
set WHISPER_COMPUTE_TYPE=float16     # GPU compute type
set BACKEND_PORT=8001                # Change backend port
set FRONTEND_PORT=5174               # Change frontend port
```

### Build-time Configuration

Edit in `app_launcher.py`:
```python
APP_NAME = "Meeting Whisperer"       # App name
ORG_NAME = "MeetingWhisperer"        # Company name
BACKEND_PORT = 8000                  # Embedded port
FRONTEND_PORT = 5173                 # Embedded port
```

See [config.example.ini](config.example.ini) for all options.

## 📦 Distribution

### Share with End Users

**Option 1: Installer** (Recommended)
```bash
# Share: launcher/output/MeetingWhisperer-Setup-1.0.0.exe
# Users run installer like any Windows app
```

**Option 2: Portable ZIP**
```bash
# Create: launcher/dist/MeetingWhisperer.zip
# Users extract and run MeetingWhisperer.exe
```

**Option 3: Cloud/Package Manager**
- Upload to GitHub Releases
- Submit to Winget
- Host on your website

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for details.

## 🐛 Troubleshooting

### Issue: Build fails

```bash
# Step 1: Check requirements
check_requirements.bat

# Step 2: Clear and rebuild
cd launcher
rmdir /s /q build dist
quickbuild.bat
```

### Issue: App won't start

```bash
# Run with logging
python app_launcher.py 2>&1

# Check logs for errors
```

### Issue: Port already in use

```python
# Edit app_launcher.py
BACKEND_PORT = 8001
FRONTEND_PORT = 5174
```

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for more solutions.

## 🎯 Common Tasks

### Update Version
```python
# app_launcher.py
APP_VERSION = "1.0.1"

# installer.iss
#define MyAppVersion "1.0.1"
```

### Add Custom Icon
1. Create 256x256 PNG image
2. Convert to .ico format
3. Save to `launcher/assets/app.ico`
4. Rebuild with PyInstaller

### Enable GPU
```python
# app_launcher.py
'WHISPER_DEVICE': 'cuda'  # Changed from 'cpu'
'WHISPER_COMPUTE_TYPE': 'float16'  # For GPU
```

### Customize Settings
See [config.example.ini](config.example.ini) and modify environment variables.

## 📊 Build Statistics

| Metric | Time | Size |
|--------|------|------|
| Full build | ~20-30 min | - |
| Quick rebuild | ~5-10 min | - |
| Executable size | - | ~500 MB |
| Installer size | - | ~200 MB |
| Install time | - | ~2-3 min |

*Times depend on system specs and internet speed*

## 📞 Support

- **Setup issues?** → [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)
- **Runtime errors?** → [TROUBLESHOOTING.md](TROUBLESHOOTING.md)  
- **Build questions?** → [README.md](README.md)
- **Distribution help?** → [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

## 🔒 Security & Maintenance

### Before Release
- [ ] Run security scan
- [ ] Update dependencies
- [ ] Test on clean Windows system
- [ ] Code review
- [ ] Sign executable (optional)

### After Release
- [ ] Monitor GitHub Issues
- [ ] Fix reported bugs
- [ ] Release patches
- [ ] Document changes in CHANGELOG

## 🚀 Next Steps

1. Run `check_requirements.bat` to verify setup
2. Run `quickbuild.bat` to build the app
3. Test the executable at `launcher/dist/MeetingWhisperer/MeetingWhisperer.exe`
4. Read [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for distribution

## 💡 Tips

- First build takes longer (downloads models)
- Subsequent builds are much faster with `quickbuild.bat`
- Use `--dev` flag for development: `app_launcher.py --dev`
- Set `--no-browser` to skip auto-opening browser
- Keep models directory in sync with backend

## 📄 License

See [LICENSE](../LICENSE) file in project root.

## 🎉 Success!

Your Windows app is ready. Now:
1. ✅ Test it thoroughly
2. ✅ Create installer
3. ✅ Distribute to users
4. ✅ Collect feedback

**Questions?** Check the documentation files above or review [README.md](README.md).

---

**Happy building!** 🎊

*Last updated: 2024*
*For latest: Check [README.md](README.md)*
