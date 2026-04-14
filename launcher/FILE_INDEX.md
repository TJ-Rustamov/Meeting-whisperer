# File Index - Windows App Builder

Complete reference of all files created in the `launcher/` directory.

## 📋 Quick Reference

| File | Type | Purpose | Size |
|------|------|---------|------|
| **START_HERE.txt** | Info | Visual overview (READ THIS FIRST!) | 8 KB |
| **GETTING_STARTED.md** | Guide | 5-minute quick start | 15 KB |
| **app_launcher.py** | Code | Main application entry point | 20 KB |
| **app_launcher.spec** | Config | PyInstaller configuration | 2 KB |
| **installer.iss** | Config | Inno Setup configuration | 6 KB |
| **build.bat** | Script | Full build script | 4 KB |
| **quickbuild.bat** | Script | Fast rebuild script | 2 KB |
| **check_requirements.bat** | Script | Verify prerequisites | 5 KB |
| **dev_server.py** | Script | Development helper | 1 KB |
| **requirements-build.txt** | Config | Build dependencies | 1 KB |
| **config.example.ini** | Config | Settings template | 5 KB |
| **README.md** | Guide | Full documentation | 25 KB |
| **INSTALLATION_GUIDE.md** | Guide | Setup instructions | 30 KB |
| **TROUBLESHOOTING.md** | Guide | Problem solving | 35 KB |
| **DEPLOYMENT_GUIDE.md** | Guide | Distribution guide | 20 KB |

---

## 🎯 By Purpose

### 📚 READ FIRST (Start here!)

#### [START_HERE.txt](START_HERE.txt)
**What:** Visual overview of the entire system
**Read:** First - gives you the big picture
**Contains:**
- What was created
- Quick start instructions
- File descriptions
- Customization options
- Next steps

#### [GETTING_STARTED.md](GETTING_STARTED.md)
**What:** Quick start guide (5 minute overview)
**Read:** After START_HERE.txt
**Contains:**
- Quick start (5 minutes)
- Prerequisites
- Build scripts overview
- Testing checklist
- Troubleshooting summary

---

### 🚀 EXECUTION (Build your app)

#### [build.bat](build.bat)
**What:** Complete build script
**When to use:** First time or clean build
**Does:**
```
1. Installs all dependencies
2. Builds React frontend
3. Creates PyInstaller executable
4. Creates Windows installer (if Inno Setup installed)
```
**Time:** 15-30 minutes
**Usage:** Double-click or `cd launcher && build.bat`

#### [quickbuild.bat](quickbuild.bat)
**What:** Fast rebuild script
**When to use:** After first build, to speed up rebuilds
**Does:**
```
1. Rebuilds frontend (if needed)
2. Rebuilds executable
3. Rebuilds installer
(skips dependency installation if already done)
```
**Time:** 5-10 minutes
**Usage:** `cd launcher && quickbuild.bat`

#### [check_requirements.bat](check_requirements.bat)
**What:** Prerequisite verification script
**When to use:** Before first build
**Does:**
```
Verifies installed:
- Python version
- Node.js version
- npm version
- Git
- FFmpeg
- PyInstaller
- Inno Setup (optional)
- Disk space
```
**Usage:** `cd launcher && check_requirements.bat`

#### [dev_server.py](dev_server.py)
**What:** Development server helper
**When to use:** During development
**Does:** Starts development servers for testing

---

### 💻 CORE APPLICATION

#### [app_launcher.py](app_launcher.py)
**What:** Main application entry point (500+ lines)
**When:** Used by every user who runs the app
**Does:**
```
When user launches MeetingWhisperer.exe:

1. Detect or use embedded Python
2. Create necessary directories:
   - %APPDATA%\MeetingWhisperer\Meeting Whisperer\data\
   - %APPDATA%\MeetingWhisperer\Meeting Whisperer\data\audio\

3. Start FastAPI backend server:
   - Host: 127.0.0.1
   - Port: 8000
   - Load models from bundled path
   - Set up database connection

4. Start frontend server:
   - Serve static files from frontend/dist
   - Port: 5173

5. Open browser to http://localhost:5173

6. Monitor processes:
   - Restart if either dies
   - Graceful shutdown on exit

7. Handle system signals (Ctrl+C)
```

**Key Classes:**
- `AppConfig` - Manages paths and configuration
- `ProcessManager` - Manages backend/frontend processes

**Configuration Options** (environment variables):
```python
BACKEND_PORT = 8000
FRONTEND_PORT = 5173
APP_NAME = "Meeting Whisperer"
ORG_NAME = "MeetingWhisperer"
```

**Customizable:**
- Ports
- App name
- Device (CPU/GPU)
- Model settings
- Database location

---

### ⚙️ CONFIGURATION FILES

#### [app_launcher.spec](app_launcher.spec)
**What:** PyInstaller configuration file
**When:** Used during build by PyInstaller
**Contains:**
```
What to bundle:
- app_launcher.py (entry point)
- backend/app/ (all source code)
- frontend/dist/ (built React app)
- models/faster-whisper-base.en/ (ML models)
- All Python dependencies

Settings:
- console=False (no console window)
- onefile=False (directory structure)
- icon path
- hidden imports (torch, fastapi, etc.)
```

#### [installer.iss](installer.iss)
**What:** Inno Setup installer configuration
**When:** Used during build to create Windows installer
**Contains:**
```
Installer settings:
- Version number
- Installation directory (Program Files)
- Start Menu shortcuts
- Optional: Desktop icon
- Optional: Startup task
- Firewall exceptions
- Uninstaller

Files to include:
- All files from PyInstaller dist/
```

#### [requirements-build.txt](requirements-build.txt)
**What:** Python dependencies for building
**When:** Installed before first build
**Contains:**
```
pyinstaller==6.9.0
psutil==6.0.0
fastapi==0.115.6
uvicorn[standard]==0.32.1
And all backend dependencies...
```

#### [config.example.ini](config.example.ini)
**What:** Configuration template
**When:** Reference for customization
**Contains:**
```
Sections:
[Application]
[Backend]
[Transcription]
[Voice Activity Detection]
[PostProcessing]
[Frontend]
[Performance]
[Security]
[Debug]
```

---

### 📖 DOCUMENTATION

#### [README.md](README.md)
**What:** Complete build documentation
**Read:** For detailed build information
**Contains:**
- Overview
- Prerequisites checklist
- Build instructions (automated & manual)
- Directory structure
- File descriptions
- Configuration & environment variables
- Customization guide
- Testing
- Troubleshooting
- Distribution
- Performance optimization
- Advanced configuration
- Version updates

#### [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)
**What:** Step-by-step setup guide
**Read:** If you need help installing prerequisites
**Contains:**
- System requirements
- Step-by-step installation:
  1. Install Visual Studio Build Tools
  2. Install Python
  3. Install Node.js
  4. Install Git
  5. Install FFmpeg
  6. Install PyInstaller
  7. Install Inno Setup (optional)
  8. Install project dependencies
- Verification tests
- Building the app
- Directory structure
- Common installation issues

#### [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
**What:** Problem-solving guide
**Read:** When something breaks
**Contains:**
- **Build Issues:**
  - Python not found
  - Node.js not found
  - PyInstaller fails
  - Frontend build fails
  - FFmpeg not found
  - Out of memory
  - Port already in use

- **Runtime Issues:**
  - App crashes
  - Cannot find module
  - Database locked
  - Frontend won't load
  - Audio recording doesn't work
  - Transcription is slow

- **Installation Issues:**
  - Installer fails with permission error
  - Cannot uninstall
  - Version already installed

- **Model Issues:**
  - Models fail to download
  - Wrong model loaded

- **Performance Issues:**
  - High memory usage
  - CPU usage very high
  - Slow file operations

- **Network Issues:**
  - Cannot communicate with backend
  - CORS errors

- **Debugging:**
  - Enable debug logging
  - Check application logs
  - Use Task Manager

#### [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
**What:** Distribution strategies
**Read:** When you're ready to share with users
**Contains:**
- **Distribution Options:**
  - Windows Installer (recommended)
  - Portable Executable
  - Cloud Deployment
  - Package Managers

- **Pre-deployment:**
  - Testing checklist
  - Version control checklist
  - Security checklist

- **Building Release:**
  - Clean build
  - Version update
  - Code signing
  - Checksum creation

- **Installer Distribution:**
  - Website hosting
  - GitHub Releases
  - Package managers (Winget, Scoop)

- **Updates:**
  - Semantic versioning
  - Update process
  - Automatic updates

- **Support:**
  - Support channels
  - Analytics (optional)
  - Feedback forms

---

## 📂 Directory Structure

```
launcher/
├── 📄 START_HERE.txt                 ← READ THIS FIRST!
├── 📖 GETTING_STARTED.md             ← Quick start
├── 📖 README.md                      ← Full docs
├── 📖 INSTALLATION_GUIDE.md          ← Setup help
├── 📖 TROUBLESHOOTING.md             ← Problem solving
├── 📖 DEPLOYMENT_GUIDE.md            ← Distribution
├── 📋 FILE_INDEX.md                  ← You are here
│
├── 💻 Core Application
│   ├── app_launcher.py               (main entry point)
│   ├── dev_server.py                 (dev helper)
│   └── requirements-build.txt        (dependencies)
│
├── ⚙️ Configuration
│   ├── app_launcher.spec             (PyInstaller config)
│   ├── installer.iss                 (Inno Setup config)
│   └── config.example.ini            (settings template)
│
├── 🔨 Build Scripts
│   ├── build.bat                     (full build)
│   ├── quickbuild.bat                (fast rebuild)
│   ├── quickbuild.py                 (Python version)
│   └── check_requirements.bat        (verify prerequisites)
│
├── 📦 Output (generated during build)
│   ├── build/                        (PyInstaller temp)
│   ├── dist/                         (built executable)
│   │   └── MeetingWhisperer/
│   │       ├── MeetingWhisperer.exe  (portable app)
│   │       ├── _internal/            (dependencies)
│   │       └── [...files...]
│   └── output/                       (installer)
│       └── MeetingWhisperer-Setup-1.0.0.exe
│
└── 📁 Assets (optional)
    └── assets/
        └── app.ico                   (window icon)
```

---

## 🔄 Usage Flow

### First Time Setup

```
1. Download/extract project
   ↓
2. Read: START_HERE.txt
   ↓
3. Run: check_requirements.bat
   ├─ What: Verify prerequisites installed
   ├─ Time: 1 minute
   └─ If fails: See INSTALLATION_GUIDE.md
   ↓
4. Run: build.bat  
   ├─ What: Full build with all steps
   ├─ Time: 15-30 minutes
   └─ Generates: MeetingWhisperer.exe + Setup.exe
   ↓
5. Test: launcher/dist/MeetingWhisperer/MeetingWhisperer.exe
   ├─ What: Run the built app
   ├─ Expected: App opens in browser
   └─ If fails: See TROUBLESHOOTING.md
   ↓
6. Read: DEPLOYMENT_GUIDE.md
   └─ What: How to distribute to users
```

### Subsequent Builds

```
1. Make code changes (backend or frontend)
   ↓
2. Run: quickbuild.bat
   ├─ What: Fast rebuild (skip dependency install)
   ├─ Time: 5-10 minutes
   └─ Generates: Updated MeetingWhisperer.exe + Setup.exe
   ↓
3. Test new build
```

### For Troubleshooting

```
Issue → TROUBLESHOOTING.md
  ├─ Build failed → Check requirements → Try quickbuild
  ├─ App crashes → Check logs → Modify app_launcher.py
  ├─ Port in use → Change port in app_launcher.py → Rebuild
  └─ Other → Read full documentation or check README
```

---

## 🎯 Find What You Need

**I want to build the app**
→ GETTING_STARTED.md + quickbuild.bat

**I need help installing prerequisites**
→ INSTALLATION_GUIDE.md + check_requirements.bat

**Something is broken**
→ TROUBLESHOOTING.md

**I want to share with users**
→ DEPLOYMENT_GUIDE.md

**I want full technical details**
→ README.md

**I'm confused where to start**
→ START_HERE.txt first, then GETTING_STARTED.md

**I want to customize the app**
→ README.md + Customization section

**I want to understand how it works**
→ app_launcher.py + README.md Architecture section

---

## 📊 File Statistics

Total Created: 15 files
- Scripts: 4 (.bat + .py)
- Configuration: 4 (.spec, .iss, .txt, .ini)
- Documentation: 6 (.md files)
- Visual guides: 1 (.txt)

Total Size: ~180 KB
Total Documentation: ~130 KB
Total Code: ~30 KB
Total Config: ~20 KB

---

## ✅ Completion Status

All files created and ready to use:

✅ Application code (app_launcher.py)
✅ Build configuration (PyInstaller spec)
✅ Installer configuration (Inno Setup)
✅ Build scripts (Windows batch)
✅ Requirements files
✅ Comprehensive documentation
✅ Quick start materials
✅ Troubleshooting guides
✅ Deployment guides
✅ Configuration templates

**Status: READY TO BUILD** 🎉

---

## 🚀 Next Steps

1. Open: [START_HERE.txt](START_HERE.txt)
2. Run: `check_requirements.bat`
3. Run: `quickbuild.bat`
4. Test: `launcher\dist\MeetingWhisperer\MeetingWhisperer.exe`

Good luck! 🎊

---

*Last updated: 2024*
*Questions? See the documentation files above or review README.md*
