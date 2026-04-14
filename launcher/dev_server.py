#!/usr/bin/env python3
"""
Helper script to serve frontend with the app launcher for development
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from threading import Thread

def run_frontend_dev():
    """Run frontend in development mode"""
    frontend_dir = Path(__file__).parent.parent / 'frontend'
    
    print("Starting Vite development server...")
    os.chdir(str(frontend_dir))
    subprocess.run([sys.executable, '-m', 'http.server', '5173'])

def main():
    """Main function"""
    launcher_dir = Path(__file__).parent
    
    # Start frontend dev server in background
    frontend_thread = Thread(target=run_frontend_dev, daemon=True)
    frontend_thread.start()
    
    # Give it time to start
    time.sleep(2)
    
    # Start app launcher
    result = subprocess.run([sys.executable, str(launcher_dir / 'app_launcher.py'), '--dev'])
    return result.returncode

if __name__ == '__main__':
    sys.exit(main())
