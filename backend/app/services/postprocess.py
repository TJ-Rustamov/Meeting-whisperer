from __future__ import annotations

import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.meeting import Meeting, ProcessedTranscriptSegment, TranscriptSegment
from app.services.transcriber import get_transcriber

logger = logging.getLogger(__name__)


@dataclass
class _RawSegment:
    start: float
    end: float
    text: str


@dataclass
class _DiarizationSpan:
    start: float
    end: float
    speaker: str


_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="postprocess")
_jobs_in_flight: set[int] = set()
_jobs_lock = threading.Lock()


def _cleanup_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if not cleaned:
        return ""
    cleaned = re.sub(r"\b(uh+|um+)\b", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return ""
    cleaned = cleaned[0].upper() + cleaned[1:]
    if cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned


def _load_raw_segments(audio_path: str) -> list[_RawSegment]:
    transcriber = get_transcriber()
    if transcriber.fake_model or transcriber.model is None:
        raise RuntimeError("Post-processing requires a real Whisper model.")
    segments, _ = transcriber.model.transcribe(
        audio_path,
        language=settings.whisper_language,
        beam_size=settings.postprocess_beam_size,
        best_of=settings.postprocess_best_of,
        temperature=settings.postprocess_temperature,
        word_timestamps=False,
        vad_filter=True,
        condition_on_previous_text=True,
        without_timestamps=False,
    )
    out: list[_RawSegment] = []
    for seg in segments:
        text = _cleanup_text(seg.text or "")
        if not text:
            continue
        out.append(
            _RawSegment(
                start=float(seg.start or 0.0),
                end=float(seg.end or seg.start or 0.0),
                text=text,
            )
        )
    return out


def _chunk_text_for_diarization(text: str, max_chars: int) -> list[str]:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if not sentences:
        return []
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if not current:
            current = sentence
            continue
        candidate = f"{current} {sentence}".strip()
        if len(candidate) <= max_chars:
            current = candidate
        else:
            chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)

    out: list[str] = []
    for chunk in chunks:
        if len(chunk) <= max_chars:
            out.append(chunk)
            continue
        words = chunk.split()
        if not words:
            continue
        running: list[str] = []
        for word in words:
            probe = (" ".join(running + [word])).strip()
            if running and len(probe) > max_chars:
                out.append(" ".join(running).strip())
                running = [word]
            else:
                running.append(word)
        if running:
            out.append(" ".join(running).strip())
    return [c for c in out if c]


def _split_for_diarization(segments: list[_RawSegment]) -> list[_RawSegment]:
    out: list[_RawSegment] = []
    for seg in segments:
        seg_text = (seg.text or "").strip()
        seg_duration = max(0.01, seg.end - seg.start)
        if seg_duration <= settings.postprocess_segment_max_sec and len(seg_text) <= settings.postprocess_segment_max_chars:
            out.append(seg)
            continue

        chunks = _chunk_text_for_diarization(seg_text, settings.postprocess_segment_max_chars)
        if len(chunks) <= 1:
            out.append(seg)
            continue
        total_weight = sum(max(1, len(chunk)) for chunk in chunks)
        cursor = seg.start
        for idx, chunk in enumerate(chunks):
            weight = max(1, len(chunk))
            chunk_dur = seg_duration * (weight / total_weight)
            if idx == len(chunks) - 1:
                chunk_end = seg.end
            else:
                chunk_end = min(seg.end, cursor + chunk_dur)
            out.append(_RawSegment(start=cursor, end=max(cursor + 0.01, chunk_end), text=chunk))
            cursor = chunk_end
    return out


def _diarize_pyannote(
    audio_path: str,
    *,
    min_speakers: int | None = None,
    max_speakers: int | None = None,
    num_speakers: int | None = None,
) -> list[_DiarizationSpan]:
    import av  # type: ignore
    import numpy as np  # type: ignore
    import torch  # type: ignore
    from pyannote.audio import Pipeline  # type: ignore

    container = av.open(audio_path)
    audio_stream = next((stream for stream in container.streams if stream.type == "audio"), None)
    if audio_stream is None:
        raise RuntimeError(f"No audio stream found for diarization input: {audio_path}")

    chunks: list[np.ndarray] = []
    sample_rate: int | None = None
    for frame in container.decode(audio_stream):
        raw = frame.to_ndarray()
        if raw.ndim == 2:
            raw = raw.mean(axis=0)
        if np.issubdtype(raw.dtype, np.integer):
            raw_f32 = raw.astype(np.float32) / float(np.iinfo(raw.dtype).max)
        else:
            raw_f32 = raw.astype(np.float32)
        chunks.append(raw_f32)
        sample_rate = int(frame.sample_rate or sample_rate or 16000)

    if not chunks or sample_rate is None:
        raise RuntimeError(f"Decoded audio is empty for diarization input: {audio_path}")

    waveform = np.concatenate(chunks, axis=0)
    waveform_tensor = torch.from_numpy(waveform).unsqueeze(0)
    logger.info(
        "Diarization input decoded path=%s sample_rate=%s samples=%s duration_sec=%.2f",
        audio_path,
        sample_rate,
        waveform_tensor.shape[-1],
        waveform_tensor.shape[-1] / float(sample_rate),
    )

    token = settings.postprocess_hf_token or None
    pipeline = Pipeline.from_pretrained(settings.postprocess_pyannote_model, use_auth_token=token)
    kwargs: dict[str, int] = {}
    if min_speakers is not None:
        kwargs["min_speakers"] = min_speakers
    if max_speakers is not None:
        kwargs["max_speakers"] = max_speakers
    if num_speakers is not None and num_speakers > 0:
        kwargs["num_speakers"] = num_speakers
    annotation = pipeline(
        {
            "waveform": waveform_tensor,
            "sample_rate": sample_rate,
        },
        **kwargs,
    )
    spans: list[_DiarizationSpan] = []
    for turn, _, speaker in annotation.itertracks(yield_label=True):
        spans.append(
            _DiarizationSpan(
                start=float(turn.start),
                end=float(turn.end),
                speaker=str(speaker),
            )
        )
    spans.sort(key=lambda s: (s.start, s.end))
    return spans


def _fallback_diarization(segments: list[_RawSegment], originals: list[TranscriptSegment]) -> list[_DiarizationSpan]:
    if not originals:
        return [_DiarizationSpan(start=s.start, end=s.end, speaker="speaker_1") for s in segments]
    spans: list[_DiarizationSpan] = []
    for s in segments:
        best_overlap = 0.0
        best_speaker = "speaker_1"
        for orig in originals:
            overlap = max(0.0, min(s.end, orig.end_time) - max(s.start, orig.start_time))
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = orig.speaker_label
        spans.append(_DiarizationSpan(start=s.start, end=s.end, speaker=best_speaker))
    return spans


def _label_for_segment(seg: _RawSegment, spans: list[_DiarizationSpan]) -> str:
    if not spans:
        return "speaker_1"
    best_overlap = 0.0
    best_speaker = spans[0].speaker
    for span in spans:
        overlap = max(0.0, min(seg.end, span.end) - max(seg.start, span.start))
        if overlap > best_overlap:
            best_overlap = overlap
            best_speaker = span.speaker
    if best_overlap > 0:
        return best_speaker
    midpoint = (seg.start + seg.end) / 2.0
    nearest = min(spans, key=lambda span: abs(((span.start + span.end) / 2.0) - midpoint))
    return nearest.speaker


def _speaker_count(spans: list[_DiarizationSpan]) -> int:
    return len({span.speaker for span in spans})


def _extract_source(label: str) -> str | None:
    value = (label or "").strip().lower()
    if ":" not in value:
        return None
    prefix = value.split(":", 1)[0].strip()
    if prefix in {"mic", "system", "mixed"}:
        return prefix
    return None


def _source_for_segment(seg: _RawSegment, originals: list[TranscriptSegment]) -> str:
    if not originals:
        return "mixed"
    best_overlap = 0.0
    best_source = "mixed"
    for orig in originals:
        overlap = max(0.0, min(seg.end, orig.end_time) - max(seg.start, orig.start_time))
        if overlap > best_overlap:
            best_overlap = overlap
            best_source = _extract_source(orig.speaker_label) or "mixed"
    return best_source


def _set_status(
    meeting_id: int,
    *,
    status: str,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    error: str | None = None,
    has_processed: bool | None = None,
) -> None:
    db = SessionLocal()
    try:
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            return
        meeting.processed_status = status
        meeting.processed_started_at = started_at
        meeting.processed_finished_at = finished_at
        meeting.processed_error = error
        if has_processed is not None:
            meeting.has_processed_transcript = has_processed
        db.commit()
    finally:
        db.close()


def _run_postprocess_job(meeting_id: int) -> None:
    started = datetime.utcnow()
    _set_status(meeting_id, status="running", started_at=started, finished_at=None, error=None)
    db = SessionLocal()
    try:
        meeting = (
            db.query(Meeting)
            .options(selectinload(Meeting.transcript_segments))
            .filter(Meeting.id == meeting_id)
            .first()
        )
        if not meeting:
            raise RuntimeError("Meeting not found")
        if not meeting.audio_file_path:
            raise RuntimeError("No audio uploaded for this meeting yet.")

        raw_segments = _split_for_diarization(_load_raw_segments(meeting.audio_file_path))
        raw_total_sec = sum(max(0.0, seg.end - seg.start) for seg in raw_segments)
        logger.info(
            "Post-process transcription prepared meeting_id=%s raw_segments=%s total_speech_sec=%.2f use_pyannote=%s",
            meeting_id,
            len(raw_segments),
            raw_total_sec,
            settings.postprocess_use_pyannote,
        )
        if settings.postprocess_use_pyannote:
            try:
                forced_num = settings.postprocess_force_num_speakers or None
                logger.info(
                    "Diarization start meeting_id=%s model=%s token_set=%s forced_num=%s retry_multi=%s",
                    meeting_id,
                    settings.postprocess_pyannote_model,
                    bool(settings.postprocess_hf_token),
                    forced_num,
                    settings.postprocess_retry_multi_speaker,
                )
                diarization = _diarize_pyannote(meeting.audio_file_path, num_speakers=forced_num)
                logger.info(
                    "Diarization first pass meeting_id=%s spans=%s speakers=%s",
                    meeting_id,
                    len(diarization),
                    _speaker_count(diarization),
                )
                if (
                    settings.postprocess_retry_multi_speaker
                    and len(raw_segments) >= settings.postprocess_retry_min_segments
                    and _speaker_count(diarization) <= 1
                ):
                    logger.info(
                        "Diarization retry triggered meeting_id=%s raw_segments=%s min_speakers=%s max_speakers=%s",
                        meeting_id,
                        len(raw_segments),
                        settings.postprocess_retry_min_speakers,
                        settings.postprocess_retry_max_speakers,
                    )
                    retry_spans = _diarize_pyannote(
                        meeting.audio_file_path,
                        min_speakers=settings.postprocess_retry_min_speakers,
                        max_speakers=settings.postprocess_retry_max_speakers,
                        num_speakers=forced_num,
                    )
                    if _speaker_count(retry_spans) > _speaker_count(diarization):
                        logger.info(
                            "Diarization retry improved speaker split meeting_id=%s speakers=%s->%s",
                            meeting_id,
                            _speaker_count(diarization),
                            _speaker_count(retry_spans),
                        )
                        diarization = retry_spans
                logger.info(
                    "Diarization result meeting_id=%s spans=%s speakers=%s segments=%s",
                    meeting_id,
                    len(diarization),
                    _speaker_count(diarization),
                    len(raw_segments),
                )
            except Exception as exc:
                logger.exception(
                    "Diarization failed meeting_id=%s model=%s token_set=%s: %s",
                    meeting_id,
                    settings.postprocess_pyannote_model,
                    bool(settings.postprocess_hf_token),
                    exc,
                )
                try:
                    import torch  # type: ignore
                    import torchaudio  # type: ignore

                    logger.warning(
                        "Diarization dependency versions meeting_id=%s torch=%s torchaudio=%s has_AudioMetaData=%s",
                        meeting_id,
                        getattr(torch, "__version__", "unknown"),
                        getattr(torchaudio, "__version__", "unknown"),
                        hasattr(torchaudio, "AudioMetaData"),
                    )
                except Exception as version_exc:
                    logger.warning("Unable to inspect torch/torchaudio versions: %s", version_exc)
                if not settings.postprocess_allow_simple_fallback:
                    raise RuntimeError(f"ML diarization failed: {exc}") from exc
                logger.warning("ML diarization unavailable, using fallback labels: %s", exc)
                diarization = _fallback_diarization(raw_segments, meeting.transcript_segments)
                logger.info(
                    "Fallback diarization applied meeting_id=%s spans=%s speakers=%s",
                    meeting_id,
                    len(diarization),
                    _speaker_count(diarization),
                )
        else:
            diarization = _fallback_diarization(raw_segments, meeting.transcript_segments)
            logger.info(
                "Pyannote disabled; fallback diarization applied meeting_id=%s spans=%s speakers=%s",
                meeting_id,
                len(diarization),
                _speaker_count(diarization),
            )

        db.query(ProcessedTranscriptSegment).filter(ProcessedTranscriptSegment.meeting_id == meeting_id).delete()
        for seg in raw_segments:
            source_label = _source_for_segment(seg, meeting.transcript_segments)
            diarized_speaker = _label_for_segment(seg, diarization)
            db.add(
                ProcessedTranscriptSegment(
                    meeting_id=meeting_id,
                    speaker_label=f"{source_label}:{diarized_speaker}",
                    start_time=seg.start,
                    end_time=seg.end,
                    text=seg.text,
                )
            )
        meeting.processed_status = "done"
        meeting.processed_started_at = started
        meeting.processed_finished_at = datetime.utcnow()
        meeting.processed_error = None
        meeting.has_processed_transcript = len(raw_segments) > 0
        db.commit()
        logger.info(
            "Post-processing complete meeting_id=%s segments=%s",
            meeting_id,
            len(raw_segments),
        )
    except Exception as exc:
        logger.exception("Post-processing failed meeting_id=%s: %s", meeting_id, exc)
        _set_status(
            meeting_id,
            status="failed",
            finished_at=datetime.utcnow(),
            error=str(exc)[:2000],
            has_processed=False,
        )
    finally:
        db.close()
        with _jobs_lock:
            _jobs_in_flight.discard(meeting_id)


def enqueue_postprocess(meeting_id: int) -> bool:
    with _jobs_lock:
        if meeting_id in _jobs_in_flight:
            return False
        _jobs_in_flight.add(meeting_id)
    _set_status(meeting_id, status="queued", started_at=None, finished_at=None, error=None, has_processed=False)
    _executor.submit(_run_postprocess_job, meeting_id)
    return True
