from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _bundle_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", _base_dir())).resolve()
    return _base_dir()


def _set_default_env() -> tuple[str, int]:
    base = _base_dir()
    bundle = _bundle_dir()
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "8000"))

    if getattr(sys, "frozen", False):
        local_app_data = Path(os.getenv("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        data_dir = (local_app_data / "MeetingWhisperer" / "data").resolve()
    else:
        data_dir = (base / "data").resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "audio").mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("DATA_DIR", str(data_dir))
    os.environ.setdefault("AUDIO_DIR", str((data_dir / "audio").resolve()))
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{data_dir.joinpath('meetings.db').as_posix()}")
    os.environ.setdefault("WHISPER_MODEL_PATH", str((bundle / "models" / "faster-whisper-base.en").resolve()))
    os.environ.setdefault("FRONTEND_DIST_DIR", str((bundle / "frontend_dist").resolve()))
    os.environ.setdefault("CORS_ORIGINS", f"http://{host}:{port},http://localhost:5173,http://127.0.0.1:5173")
    return host, port


def _open_browser(url: str) -> None:
    time.sleep(1.2)
    webbrowser.open(url)


def main() -> None:
    host, port = _set_default_env()
    from app.main import app as fastapi_app

    app_url = f"http://{host}:{port}"

    if os.getenv("OPEN_BROWSER_ON_START", "1").lower() in {"1", "true", "yes"}:
        threading.Thread(target=_open_browser, args=(app_url,), daemon=True).start()

    uvicorn.run(fastapi_app, host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
