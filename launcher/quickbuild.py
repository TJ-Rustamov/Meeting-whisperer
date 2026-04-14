#!/usr/bin/env python3
"""
Quick build script - builds everything in one go
Requires: build.bat to be run first or all prerequisites installed
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    print("\n" + "="*50)
    print("Meeting Whisperer - Quick Build")
    print("="*50 + "\n")
    
    # Step 1: Build frontend
    print("[1/3] Building frontend...")
    frontend_dir = project_root / 'frontend'
    result = subprocess.run(
        ['npm', 'run', 'build'],
        cwd=str(frontend_dir),
        shell=sys.platform == 'win32'
    )
    if result.returncode != 0:
        print("ERROR: Frontend build failed")
        return 1
    print("✓ Frontend built\n")
    
    # Step 2: PyInstaller
    print("[2/3] Creating executable...")
    result = subprocess.run(
        ['pyinstaller', '--clean', 'app_launcher.spec', '--distpath', 'dist', '--buildpath', 'build'],
        cwd=str(script_dir),
        shell=sys.platform == 'win32'
    )
    if result.returncode != 0:
        print("ERROR: PyInstaller build failed")
        return 1
    print("✓ Executable created\n")
    
    # Step 3: Create installer
    print("[3/3] Creating installer...")
    try:
        result = subprocess.run(
            [r'C:\Program Files (x86)\Inno Setup 6\ISCC.exe', 'installer.iss'],
            cwd=str(script_dir),
            shell=False
        )
        if result.returncode == 0:
            print("✓ Installer created\n")
        else:
            print("⚠ Inno Setup not found or failed (optional)\n")
    except FileNotFoundError:
        print("⚠ Inno Setup not installed (optional)\n")
        print("Install from: https://jrsoftware.org/isdl.php\n")
    
    print("="*50)
    print("✓ Build completed!")
    print("="*50)
    print(f"\nOutput locations:")
    exe_path = script_dir / 'dist' / 'MeetingWhisperer' / 'MeetingWhisperer.exe'
    if exe_path.exists():
        print(f"  Executable: {exe_path}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
