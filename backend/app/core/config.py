from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


def _project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[3]


def _default_model_path() -> str:
    return str((_project_root() / "models" / "faster-whisper-base.en").resolve())


def _default_frontend_dist_path() -> str:
    return str((_project_root() / "frontend_dist").resolve())


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Meeting Whisperer API")
    api_prefix: str = "/api"
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173"
        ).split(",")
        if origin.strip()
    )
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/meetings.db")
    data_dir: Path = Path(os.getenv("DATA_DIR", "./data")).resolve()
    audio_dir: Path = Path(os.getenv("AUDIO_DIR", "./data/audio")).resolve()
    whisper_model_path: str = os.getenv("WHISPER_MODEL_PATH", _default_model_path())
    whisper_device: str = os.getenv("WHISPER_DEVICE", "cpu")
    whisper_compute_type: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    whisper_language: str = os.getenv("WHISPER_LANGUAGE", "en")
    whisper_beam_size: int = int(os.getenv("WHISPER_BEAM_SIZE", "2"))
    whisper_best_of: int = int(os.getenv("WHISPER_BEST_OF", "2"))
    whisper_patience: float = float(os.getenv("WHISPER_PATIENCE", "0.8"))
    whisper_temperature: float = float(os.getenv("WHISPER_TEMPERATURE", "0.0"))
    whisper_no_speech_threshold: float = float(os.getenv("WHISPER_NO_SPEECH_THRESHOLD", "0.6"))
    whisper_log_prob_threshold: float = float(os.getenv("WHISPER_LOG_PROB_THRESHOLD", "-1.0"))
    whisper_initial_prompt: str = os.getenv("WHISPER_INITIAL_PROMPT", "")
    ws_sample_rate: int = int(os.getenv("WS_SAMPLE_RATE", "16000"))
    silero_threshold: float = float(os.getenv("SILERO_THRESHOLD", "0.35"))
    vad_hangover_frames: int = int(os.getenv("VAD_HANGOVER_FRAMES", "8"))
    vad_min_rms_floor: int = int(os.getenv("VAD_MIN_RMS_FLOOR", "80"))
    vad_quiet_multiplier: float = float(os.getenv("VAD_QUIET_MULTIPLIER", "0.65"))
    partial_interval_sec: float = float(os.getenv("PARTIAL_INTERVAL_SEC", "0.45"))
    silence_finalize_sec: float = float(os.getenv("SILENCE_FINALIZE_SEC", "0.45"))
    ws_max_utterance_sec: float = float(os.getenv("WS_MAX_UTTERANCE_SEC", "4.0"))
    live_overlap_sec: float = float(os.getenv("LIVE_OVERLAP_SEC", "0.35"))
    partial_max_audio_sec: float = float(os.getenv("PARTIAL_MAX_AUDIO_SEC", "10.0"))
    partial_min_new_audio_sec: float = float(os.getenv("PARTIAL_MIN_NEW_AUDIO_SEC", "0.15"))
    postprocess_beam_size: int = int(os.getenv("POSTPROCESS_BEAM_SIZE", "6"))
    postprocess_best_of: int = int(os.getenv("POSTPROCESS_BEST_OF", "6"))
    postprocess_temperature: float = float(os.getenv("POSTPROCESS_TEMPERATURE", "0.0"))
    postprocess_use_pyannote: bool = os.getenv("POSTPROCESS_USE_PYANNOTE", "1").lower() in {"1", "true", "yes"}
    postprocess_pyannote_model: str = os.getenv("POSTPROCESS_PYANNOTE_MODEL", "pyannote/speaker-diarization-3.1")
    postprocess_hf_token: str = os.getenv("POSTPROCESS_HF_TOKEN", "")
    postprocess_diarization_timeout_sec: float = float(os.getenv("POSTPROCESS_DIARIZATION_TIMEOUT_SEC", "600"))
    postprocess_retry_multi_speaker: bool = os.getenv("POSTPROCESS_RETRY_MULTI_SPEAKER", "1").lower() in {
        "1",
        "true",
        "yes",
    }
    postprocess_force_num_speakers: int = int(os.getenv("POSTPROCESS_FORCE_NUM_SPEAKERS", "0"))
    postprocess_retry_min_speakers: int = int(os.getenv("POSTPROCESS_RETRY_MIN_SPEAKERS", "2"))
    postprocess_retry_max_speakers: int = int(os.getenv("POSTPROCESS_RETRY_MAX_SPEAKERS", "8"))
    postprocess_retry_min_segments: int = int(os.getenv("POSTPROCESS_RETRY_MIN_SEGMENTS", "6"))
    postprocess_segment_max_sec: float = float(os.getenv("POSTPROCESS_SEGMENT_MAX_SEC", "8.0"))
    postprocess_segment_max_chars: int = int(os.getenv("POSTPROCESS_SEGMENT_MAX_CHARS", "180"))
    postprocess_allow_simple_fallback: bool = os.getenv("POSTPROCESS_ALLOW_SIMPLE_FALLBACK", "0").lower() in {
        "1",
        "true",
        "yes",
    }
    fake_model: bool = os.getenv("STT_FAKE_MODEL", "0").lower() in {"1", "true", "yes"}
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
    ws_debug_interval_frames: int = int(os.getenv("WS_DEBUG_INTERVAL_FRAMES", "50"))
    frontend_dist_dir: Path = Path(os.getenv("FRONTEND_DIST_DIR", _default_frontend_dist_path())).resolve()


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.audio_dir.mkdir(parents=True, exist_ok=True)
