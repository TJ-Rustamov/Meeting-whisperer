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

    def transcribe_pcm16(self, audio_bytes: bytes, boost_quality: bool = False) -> str:
        if not audio_bytes:
            return ""
        started = time.time()
        if self.fake_model:
            ms = len(audio_bytes) / 2 / settings.ws_sample_rate * 1000
            text = f"[fake transcript {int(ms)}ms]"
            logger.debug("Fake transcription generated for %s bytes", len(audio_bytes))
            return text

        assert self.model is not None
        
        # Boost quality parameters for mic-primary audio
        beam_size = settings.whisper_beam_size
        best_of = settings.whisper_best_of
        temperature = settings.whisper_temperature
        
        if boost_quality:
            beam_size = max(10, beam_size + 5)
            best_of = max(5, best_of + 2)
            temperature = max(0.0, temperature - 0.1)
            logger.debug(
                "Quality boost enabled: beam_size=%d best_of=%d temperature=%.2f",
                beam_size,
                best_of,
                temperature,
            )
        
        audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
        audio = audio_int16.astype(np.float32) / 32768.0
        segments, _ = self.model.transcribe(
            audio,
            language=settings.whisper_language,
            beam_size=beam_size,
            best_of=best_of,
            patience=settings.whisper_patience,
            temperature=temperature,
            no_speech_threshold=settings.whisper_no_speech_threshold,
            log_prob_threshold=settings.whisper_log_prob_threshold,
            vad_filter=False,
            condition_on_previous_text=False,
            without_timestamps=True,
            initial_prompt=settings.whisper_initial_prompt or None,
        )
        text = " ".join(segment.text.strip() for segment in segments if segment.text.strip())
        final_text = text.strip()
        
        # Detect hallucination pattern: same phrase repeated many times
        if final_text:
            words = final_text.split()
            if len(words) > 20:  # Check longer transcripts for repetition
                # Check if same words appear too frequently
                word_counts = {}
                for w in words:
                    word_counts[w] = word_counts.get(w, 0) + 1
                
                # If any word appears >30% of the time, likely hallucination
                max_freq = max(word_counts.values()) if word_counts else 0
                if max_freq / len(words) > 0.3:
                    most_repeated = max(word_counts.items(), key=lambda x: x[1])
                    logger.warning(
                        "Hallucination detected: word '%s' appears %d/%d times (%.1f%%)",
                        most_repeated[0],
                        most_repeated[1],
                        len(words),
                        (most_repeated[1] / len(words)) * 100,
                    )
        
        logger.info(
            "Transcribed %s bytes in %.2fs (chars=%s%s)",
            len(audio_bytes),
            time.time() - started,
            len(final_text),
            " [quality_boosted]" if boost_quality else "",
        )
        return final_text


@lru_cache(maxsize=1)
def get_transcriber() -> WhisperTranscriber:
    started = time.time()
    transcriber = WhisperTranscriber()
    elapsed = time.time() - started
    logger.info("Whisper transcriber initialized in %.2fs (fake=%s)", elapsed, transcriber.fake_model)
    return transcriber
