#!/usr/bin/env python3
"""
Meeting Whisperer Windows App Launcher
Starts backend FastAPI server and frontend, manages lifecycle
"""

import os
import sys
import json
import shutil
import logging
import webbrowser
import time
import socket
import psutil
import signal
import atexit
from pathlib import Path
from subprocess import Popen, PIPE
from threading import Thread
from http.client import HTTPConnection
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MeetingWhisperer')

# Configuration
BACKEND_PORT = 8000
FRONTEND_PORT = 5173
APP_NAME = "Meeting Whisperer"
ORG_NAME = "MeetingWhisperer"


class AppConfig:
    """Manage application configuration and data directories"""
    
    def __init__(self):
        # Get app data directory
        if sys.platform == 'win32':
            self.app_data = Path(os.getenv('APPDATA')) / ORG_NAME / APP_NAME
        else:
            self.app_data = Path.home() / f'.{ORG_NAME.lower()}'
        
        # Get app root (where the executable/launcher is)
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            self.app_root = Path(sys.executable).parent
        else:
            # Running as script
            self.app_root = Path(__file__).parent.parent
        
        self.data_dir = self.app_data / 'data'
        self.audio_dir = self.data_dir / 'audio'
        self.db_path = self.data_dir / 'meetings.db'
        self.models_dir = self.app_root / 'models'
        
    def init_directories(self):
        """Create necessary directories"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Data directory: {self.data_dir}")


class ProcessManager:
    """Manage backend and frontend processes"""
    
    def __init__(self, config):
        self.config = config
        self.backend_process = None
        self.frontend_process = None
        self.processes_to_kill = []
        
        # Register cleanup on exit
        atexit.register(self.cleanup)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle system signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.cleanup()
        sys.exit(0)
    
    def is_port_available(self, port):
        """Check if port is available"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            result = sock.connect_ex(('localhost', port))
            return result != 0
    
    def wait_for_port(self, port, timeout=30):
        """Wait for a port to be available (service started)"""
        start = time.time()
        while time.time() - start < timeout:
            try:
                conn = HTTPConnection('localhost', port, timeout=1)
                conn.request('GET', '/health')
                resp = conn.getresponse()
                conn.close()
                if resp.status == 200:
                    logger.info(f"Service on port {port} is ready")
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        return False
    
    def start_backend(self):
        """Start FastAPI backend server"""
        logger.info("Starting backend server...")
        
        # Prepare environment
        env = os.environ.copy()
        env.update({
            'APP_NAME': APP_NAME,
            'DATABASE_URL': f'sqlite:///{self.config.db_path}',
            'DATA_DIR': str(self.config.data_dir),
            'AUDIO_DIR': str(self.config.audio_dir),
            'WHISPER_MODEL_PATH': str(self.config.models_dir / 'faster-whisper-base.en'),
            'WHISPER_LANGUAGE': 'en',
            'WHISPER_DEVICE': 'cpu',
            'WHISPER_COMPUTE_TYPE': 'int8',
            'WHISPER_BEAM_SIZE': '5',
            'WHISPER_BEST_OF': '5',
            'WHISPER_PATIENCE': '1.0',
            'WHISPER_TEMPERATURE': '0.0',
            'WHISPER_NO_SPEECH_THRESHOLD': '0.6',
            'WHISPER_LOG_PROB_THRESHOLD': '-1.0',
            'CORS_ORIGINS': f'http://localhost:5173,http://127.0.0.1:5173',
            'WS_SAMPLE_RATE': '16000',
            'SILERO_THRESHOLD': '0.35',
            'VAD_HANGOVER_FRAMES': '8',
            'VAD_MIN_RMS_FLOOR': '80',
            'VAD_QUIET_MULTIPLIER': '0.65',
            'PARTIAL_INTERVAL_SEC': '1.2',
            'SILENCE_FINALIZE_SEC': '1.0',
            'LIVE_OVERLAP_SEC': '0.35',
            'PARTIAL_MAX_AUDIO_SEC': '10.0',
            'PARTIAL_MIN_NEW_AUDIO_SEC': '0.6',
            'POSTPROCESS_BEAM_SIZE': '6',
            'POSTPROCESS_BEST_OF': '6',
            'POSTPROCESS_TEMPERATURE': '0.0',
            'POSTPROCESS_USE_PYANNOTE': '0',
            'POSTPROCESS_ALLOW_SIMPLE_FALLBACK': '1',
        })
        
        # Find backend directory
        backend_dir = self.config.app_root / 'backend'
        
        try:
            # Start backend with uvicorn
            cmd = [
                sys.executable,
                '-m', 'uvicorn',
                'app.main:app',
                '--host', '127.0.0.1',
                '--port', str(BACKEND_PORT),
                '--reload' if '--dev' in sys.argv else '--no-reload',
            ]
            
            self.backend_process = Popen(
                cmd,
                cwd=str(backend_dir),
                env=env,
                stdout=PIPE,
                stderr=PIPE,
                creationflags=0x08 if sys.platform == 'win32' else 0,
            )
            self.processes_to_kill.append(self.backend_process)
            logger.info(f"Backend process started (PID: {self.backend_process.pid})")
            
            # Wait for backend to be ready
            if self.wait_for_port(BACKEND_PORT):
                logger.info("Backend is ready!")
                return True
            else:
                logger.error("Backend failed to start within timeout")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start backend: {e}")
            return False
    
    def start_frontend(self):
        """Start frontend (development server or static serve)"""
        logger.info("Starting frontend server...")
        
        frontend_dir = self.config.app_root / 'frontend'
        
        # Check if frontend is built
        dist_dir = frontend_dir / 'dist'
        if not dist_dir.exists() or not list(dist_dir.glob('*.html')):
            logger.error(f"Frontend not built! Expected dist at: {dist_dir}")
            logger.error("Please build frontend first: cd frontend && npm run build")
            return False
        
        try:
            # Serve static files from frontend/dist using Python's http.server
            cmd = [
                sys.executable,
                '-m', 'http.server',
                str(FRONTEND_PORT),
                '--bind', '127.0.0.1',
            ]
            
            self.frontend_process = Popen(
                cmd,
                cwd=str(dist_dir),
                stdout=PIPE,
                stderr=PIPE,
                creationflags=0x08 if sys.platform == 'win32' else 0,
            )
            self.processes_to_kill.append(self.frontend_process)
            logger.info(f"Frontend process started (PID: {self.frontend_process.pid})")
            logger.info(f"Serving from: {dist_dir}")
            
            # Wait for frontend to be ready
            time.sleep(1)
            logger.info("Frontend is ready!")
            return True
                
        except Exception as e:
            logger.error(f"Failed to start frontend: {e}")
            return False
    
    def open_browser(self):
        """Open application in default browser"""
        logger.info("Opening browser...")
        url = f'http://localhost:{FRONTEND_PORT}'
        try:
            webbrowser.open(url)
            logger.info(f"Browser opened to {url}")
        except Exception as e:
            logger.warning(f"Failed to open browser: {e}")
            logger.info(f"Please open manually: {url}")
    
    def cleanup(self):
        """Clean up processes"""
        logger.info("Cleaning up...")
        for proc in self.processes_to_kill:
            try:
                if proc and proc.poll() is None:  # If still running
                    logger.info(f"Terminating process {proc.pid}")
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except:
                        proc.kill()
            except Exception as e:
                logger.error(f"Error terminating process: {e}")
    
    def monitor_processes(self):
        """Monitor processes and restart if needed"""
        while True:
            time.sleep(5)
            
            # Check backend
            if self.backend_process and self.backend_process.poll() is not None:
                logger.warning("Backend process died, attempting restart...")
                self.start_backend()
            
            # Check frontend
            if self.frontend_process and self.frontend_process.poll() is not None:
                logger.warning("Frontend process died, attempting restart...")
                self.start_frontend()


def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(description='Meeting Whisperer Application')
    parser.add_argument('--dev', action='store_true', help='Run in development mode')
    parser.add_argument('--no-browser', action='store_true', help='Do not open browser')
    args = parser.parse_args()
    
    logger.info(f"Starting {APP_NAME}...")
    
    # Initialize configuration
    config = AppConfig()
    config.init_directories()
    
    # Initialize process manager
    manager = ProcessManager(config)
    
    # Start services
    logger.info("Starting services...")
    
    if not manager.start_backend():
        logger.error("Failed to start backend")
        return 1
    
    if not manager.start_frontend():
        logger.error("Failed to start frontend")
        manager.cleanup()
        return 1
    
    # Open browser
    if not args.no_browser:
        manager.open_browser()
    
    logger.info(f"{APP_NAME} is running!")
    logger.info(f"Backend: http://localhost:{BACKEND_PORT}")
    logger.info(f"Frontend: http://localhost:{FRONTEND_PORT}")
    logger.info("Press Ctrl+C to stop")
    
    # Monitor processes
    try:
        monitor_thread = Thread(target=manager.monitor_processes, daemon=True)
        monitor_thread.start()
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        manager.cleanup()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
