from __future__ import annotations

import time
import logging
from functools import lru_cache

import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    def __init__(self) -> None:
        self.fake_model = settings.fake_model
        self.model = None
        if not self.fake_model:
            logger.info(
                "Loading Whisper model path=%s device=%s compute_type=%s",
                settings.whisper_model_path,
                settings.whisper_device,
                settings.whisper_compute_type,
            )
            from faster_whisper import WhisperModel

            self.model = WhisperModel(
                settings.whisper_model_path,
                device=settings.whisper_device,
                compute_type=settings.whisper_compute_type,
            )

    def transcribe_pcm16(self, audio_bytes: bytes) -> str:
        if not audio_bytes:
            return ""
        started = time.time()
        if self.fake_model:
            ms = len(audio_bytes) / 2 / settings.ws_sample_rate * 1000
            text = f"[fake transcript {int(ms)}ms]"
            logger.debug("Fake transcription generated for %s bytes", len(audio_bytes))
            return text

        assert self.model is not None
        audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
        audio = audio_int16.astype(np.float32) / 32768.0
        segments, _ = self.model.transcribe(
            audio,
            language=settings.whisper_language,
            beam_size=settings.whisper_beam_size,
            best_of=settings.whisper_best_of,
            patience=settings.whisper_patience,
            temperature=settings.whisper_temperature,
            no_speech_threshold=settings.whisper_no_speech_threshold,
            log_prob_threshold=settings.whisper_log_prob_threshold,
            vad_filter=False,
            condition_on_previous_text=False,
            without_timestamps=True,
            initial_prompt=settings.whisper_initial_prompt or None,
        )
        text = " ".join(segment.text.strip() for segment in segments if segment.text.strip())
        final_text = text.strip()
        logger.info(
            "Transcribed %s bytes in %.2fs (chars=%s)",
            len(audio_bytes),
            time.time() - started,
            len(final_text),
        )
        return final_text


@lru_cache(maxsize=1)
def get_transcriber() -> WhisperTranscriber:
    started = time.time()
    transcriber = WhisperTranscriber()
    elapsed = time.time() - started
    logger.info("Whisper transcriber initialized in %.2fs (fake=%s)", elapsed, transcriber.fake_model)
    return transcriber
