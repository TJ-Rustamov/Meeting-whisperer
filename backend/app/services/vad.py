from __future__ import annotations

import audioop
import logging
from collections import deque
from statistics import median

try:
    from pysilero_vad import SileroVoiceActivityDetector
except Exception:  # pragma: no cover - optional dependency fallback for packaging/runtime
    SileroVoiceActivityDetector = None

from app.core.config import settings

logger = logging.getLogger(__name__)


class HybridVAD:
    def __init__(self) -> None:
        self.vad = SileroVoiceActivityDetector() if SileroVoiceActivityDetector is not None else None
        self.hangover = 0
        self.rms_history: deque[int] = deque(maxlen=120)
        # Silero VAD commonly uses 512 samples at 16kHz (~32ms) for frame-wise calls.
        self.frame_samples = 512
        self.frame_bytes = self.frame_samples * 2
        self.frame_duration_sec = self.frame_samples / settings.ws_sample_rate
        if self.vad is None:
            logger.warning("pysilero-vad is unavailable; using RMS-only VAD fallback.")

    def process_frame(self, frame: bytes) -> tuple[bool, bool, int]:
        rms = audioop.rms(frame, 2)
        self.rms_history.append(rms)
        dynamic_floor = self._dynamic_floor()
        if self.vad is not None:
            voiced_prob = float(self.vad(frame))
            voiced = voiced_prob >= settings.silero_threshold
        else:
            voiced = rms >= dynamic_floor
        keep = voiced or rms >= dynamic_floor
        if keep:
            self.hangover = settings.vad_hangover_frames
        elif self.hangover > 0:
            keep = True
            self.hangover -= 1
        return keep, voiced, rms

    def _dynamic_floor(self) -> int:
        if not self.rms_history:
            return settings.vad_min_rms_floor
        med = int(median(self.rms_history))
        return max(settings.vad_min_rms_floor, int(med * settings.vad_quiet_multiplier))


def volume_tag_from_rms(samples: list[int]) -> str:
    if not samples:
        return "far_mic"
    avg = sum(samples) / len(samples)
    return "near_mic" if avg >= 700 else "far_mic"
