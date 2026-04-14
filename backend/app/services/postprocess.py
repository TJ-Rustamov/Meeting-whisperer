from __future__ import annotations

import logging
import re
import subprocess
import threading
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.meeting import Meeting, ProcessedTranscriptSegment, TranscriptSegment
from app.services.transcriber import get_transcriber

logger = logging.getLogger(__name__)


def _extract_audio_from_video(video_path: str) -> str:
    """
    Extract audio from a video file using ffmpeg.
    Returns the path to the extracted audio file (WAV format).
    Caller is responsible for deleting the file when done.
    """
    video_path_obj = Path(video_path)
    audio_path = video_path_obj.parent / f"{video_path_obj.stem}_extracted_audio.wav"
    
    logger.info("Extracting audio from video video_path=%s audio_path=%s", video_path, audio_path)
    
    try:
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-q:a", "9",  # quality setting for WAV
            "-y",  # overwrite output file
            str(audio_path),
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300.0,  # 5 minute timeout for extraction
        )
        if result.returncode != 0:
            logger.error(
                "ffmpeg extraction failed video_path=%s stderr=%s",
                video_path,
                result.stderr,
            )
            raise RuntimeError(f"ffmpeg audio extraction failed: {result.stderr}")
        
        if not audio_path.exists():
            raise RuntimeError(f"Audio extraction failed; output file not created: {audio_path}")
        
        file_size = audio_path.stat().st_size
        logger.info("Audio extracted successfully audio_path=%s size_bytes=%s", audio_path, file_size)
        return str(audio_path)
    except subprocess.TimeoutExpired:
        logger.error("ffmpeg extraction timed out after 300s for video_path=%s", video_path)
        audio_path.unlink(missing_ok=True)
        raise RuntimeError("Audio extraction from video timed out") from None


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


_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="postprocess")
_jobs_in_flight: set[int] = set()
_job_futures: dict[int, Future[None]] = {}  # Store futures keyed by meeting_id
_stop_requested: set[int] = set()  # Track meetings requested to stop
_jobs_lock = threading.Lock()


def should_stop_processing(meeting_id: int) -> bool:
    """Check if processing should be stopped for this meeting."""
    with _jobs_lock:
        return meeting_id in _stop_requested


def reset_postprocess_job(meeting_id: int) -> None:
    with _jobs_lock:
        _jobs_in_flight.discard(meeting_id)
        _job_futures.pop(meeting_id, None)


def cancel_postprocess_job(meeting_id: int) -> bool:
    """Request stop of a postprocessing job. Returns True if stop was requested."""
    with _jobs_lock:
        if meeting_id not in _jobs_in_flight:
            return False
        _stop_requested.add(meeting_id)
    
    logger.info("Postprocess job stop requested meeting_id=%s", meeting_id)
    return True


def _consolidate_repetitive_segments(segments: list[_RawSegment]) -> list[_RawSegment]:
    """Consolidate consecutive segments with highly similar text (hallucination detection)."""
    if len(segments) <= 1:
        return segments
    
    consolidated: list[_RawSegment] = []
    current_seg = segments[0]
    
    for seg in segments[1:]:
        # Normalize text for comparison
        curr_norm = current_seg.text.lower().strip()
        seg_norm = seg.text.lower().strip()
        
        # Check if texts are extremely similar (>80% overlap in words)
        if curr_norm and seg_norm:
            curr_words = set(curr_norm.split())
            seg_words = set(seg_norm.split())
            if len(curr_words) > 0 and len(seg_words) > 0:
                overlap = len(curr_words & seg_words) / max(len(curr_words), len(seg_words))
                
                # If massive overlap (hallucination pattern), skip the duplicate
                if overlap > 0.8 and len(seg_words) <= len(curr_words) + 5:
                    logger.warning(
                        "Skipping highly repetitive segment (%.1f%% overlap): %s...",
                        overlap * 100,
                        seg_norm[:60],
                    )
                    continue
        
        # Also check for exact substring matches (one contains the other)
        if curr_norm in seg_norm or seg_norm in curr_norm:
            logger.warning(
                "Skipping substring-duplicate segment: %s... (contained in %s...)",
                seg_norm[:60],
                curr_norm[:60],
            )
            continue
        
        # Segments are different enough, add current and start new
        consolidated.append(current_seg)
        current_seg = seg
    
    # Add the final segment
    consolidated.append(current_seg)
    
    if len(consolidated) < len(segments):
        logger.warning(
            "Consolidated %d repetitive segments down to %d",
            len(segments),
            len(consolidated),
        )
    
    return consolidated


def _deduplicate_segments(segments: list[_RawSegment]) -> list[_RawSegment]:
    """Remove exact duplicate segments by timing and text."""
    seen: set[tuple[float, float, str]] = set()
    out: list[_RawSegment] = []
    
    for seg in segments:
        key = (round(seg.start, 2), round(seg.end, 2), seg.text)
        if key not in seen:
            seen.add(key)
            out.append(seg)
    
    return out


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


def _load_raw_segments(audio_path: str, is_mic_primary: bool = False) -> list[_RawSegment]:
    transcriber = get_transcriber()
    if transcriber.fake_model or transcriber.model is None:
        raise RuntimeError("Post-processing requires a real Whisper model.")
    
    # Boost quality for mic-primary audio to prevent hallucination
    beam_size = settings.postprocess_beam_size
    best_of = settings.postprocess_best_of
    temperature = settings.postprocess_temperature
    
    if is_mic_primary:
        # Higher beam size = better quality, lower hallucination
        beam_size = max(10, beam_size + 5)
        # Higher best_of = more thorough search
        best_of = max(5, best_of + 2)
        # Lower temperature = less randomness/hallucination
        temperature = max(0.0, temperature - 0.1)
        logger.info(
            "Mic-primary audio detected: boosting transcription quality beam_size=%d best_of=%d temperature=%.2f",
            beam_size,
            best_of,
            temperature,
        )
    
    segments, _ = transcriber.model.transcribe(
        audio_path,
        language=settings.whisper_language,
        beam_size=beam_size,
        best_of=best_of,
        temperature=temperature,
        word_timestamps=False,
        vad_filter=True,
        condition_on_previous_text=False,
        without_timestamps=False,
    )
    seen: set[tuple[float, float, str]] = set()
    out: list[_RawSegment] = []
    for seg in segments:
        text = _cleanup_text(seg.text or "")
        if not text:
            continue
        key = (round(float(seg.start or 0.0), 2), round(float(seg.end or 0.0), 2), text)
        if key in seen:
            continue
        seen.add(key)
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
            
            # Ensure we don't create zero-length segments
            final_end = max(cursor + 0.01, chunk_end)
            if final_end <= cursor:
                logger.warning(
                    "Invalid segment duration in split: cursor=%.2f final_end=%.2f chunk_dur=%.2f",
                    cursor,
                    final_end,
                    chunk_dur,
                )
                final_end = cursor + 0.01
            
            out.append(_RawSegment(start=cursor, end=final_end, text=chunk))
            cursor = chunk_end
    
    # Validate output segments
    zero_duration = [seg for seg in out if seg.end <= seg.start]
    if zero_duration:
        logger.warning("_split_for_diarization produced %d zero-duration segments", len(zero_duration))
    
    return out


def _diarize_pyannote_with_timeout(
    audio_path: str,
    *,
    min_speakers: int | None = None,
    max_speakers: int | None = None,
    num_speakers: int | None = None,
    timeout_sec: float = 600.0,
) -> list[_DiarizationSpan]:
    """Wrapper around _diarize_pyannote with timeout protection."""
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(
        _diarize_pyannote,
        audio_path,
        min_speakers=min_speakers,
        max_speakers=max_speakers,
        num_speakers=num_speakers,
    )
    try:
        logger.info("Starting diarization with timeout timeout_sec=%.1f", timeout_sec)
        result = future.result(timeout=timeout_sec)
        logger.info("Diarization completed successfully")
        return result
    except FuturesTimeoutError:
        logger.warning("Diarization timed out after %.1f seconds", timeout_sec)
        raise RuntimeError(f"Diarization timed out after {timeout_sec:.1f} seconds") from None
    finally:
        executor.shutdown(wait=False)


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
    logger.info("Loading pyannote pipeline from_pretrained model=%s with_token=%s", settings.postprocess_pyannote_model, bool(token))
    pipeline = Pipeline.from_pretrained(settings.postprocess_pyannote_model, use_auth_token=token)
    logger.info("Pyannote pipeline loaded successfully")
    
    kwargs: dict[str, int] = {}
    if min_speakers is not None:
        kwargs["min_speakers"] = min_speakers
    if max_speakers is not None:
        kwargs["max_speakers"] = max_speakers
    if num_speakers is not None and num_speakers > 0:
        kwargs["num_speakers"] = num_speakers
    
    logger.info("Running diarization inference kwargs=%s", kwargs)
    annotation = pipeline(
        {
            "waveform": waveform_tensor,
            "sample_rate": sample_rate,
        },
        **kwargs,
    )
    logger.info("Diarization inference completed")
    
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
    
    # Log detailed diarization results
    unique_speakers = {s.speaker for s in spans}
    logger.debug("Diarization spans details: unique_speakers=%s", unique_speakers)
    for idx, span in enumerate(spans[:min(10, len(spans))]):  # Log first 10 spans
        logger.debug("Diarization span[%d]: start=%.2f end=%.2f duration=%.2f speaker=%s", idx, span.start, span.end, span.end - span.start, span.speaker)
    if len(spans) > 10:
        logger.debug("... and %d more spans", len(spans) - 10)
    
    return spans


def _fallback_diarization(segments: list[_RawSegment], originals: list[TranscriptSegment]) -> list[_DiarizationSpan]:
    """Fallback diarization when ML model is unavailable.
    
    Assigns speakers based on original transcription source (mic vs system).
    Uses SPEAKER_00 and SPEAKER_01 to match pyannote format.
    """
    if not originals:
        # No originals to reference - assign alternating speakers
        return [_DiarizationSpan(start=s.start, end=s.end, speaker="SPEAKER_00") for s in segments]
    
    spans: list[_DiarizationSpan] = []
    
    # First, determine which speaker corresponds to which source
    source_to_speaker: dict[str, str] = {}
    speaker_counter = 0
    
    for s in segments:
        best_overlap = 0.0
        best_source = "mixed"
        
        # Find which original segment this overlaps with
        for orig in originals:
            overlap = max(0.0, min(s.end, orig.end_time) - max(s.start, orig.start_time))
            if overlap > best_overlap:
                best_overlap = overlap
                best_source = _extract_source(orig.speaker_label) or "mixed"
        
        # Map source to speaker if not yet mapped
        if best_source not in source_to_speaker:
            source_to_speaker[best_source] = f"SPEAKER_{speaker_counter:02d}"
            speaker_counter += 1
        
        assigned_speaker = source_to_speaker[best_source]
        spans.append(_DiarizationSpan(start=s.start, end=s.end, speaker=assigned_speaker))
    
    if source_to_speaker:
        logger.debug("Fallback diarization source mapping: %s", source_to_speaker)
    
    return spans


def _label_for_segment(seg: _RawSegment, spans: list[_DiarizationSpan]) -> str:
    if not spans:
        return "speaker_1"
    
    best_overlap = 0.0
    best_speaker = spans[0].speaker
    
    # Try to find overlap with any diarization span
    for span in spans:
        overlap = max(0.0, min(seg.end, span.end) - max(seg.start, span.start))
        if overlap > best_overlap:
            best_overlap = overlap
            best_speaker = span.speaker
    
    if best_overlap > 0:
        # Good overlap found
        logger.debug(
            "Segment %.2f-%.2f: overlap=%.2f with speaker %s",
            seg.start,
            seg.end,
            best_overlap,
            best_speaker,
        )
        return best_speaker
    
    # No overlap: use smarter fallback
    # Find spans before and after the segment
    seg_midpoint = (seg.start + seg.end) / 2.0
    
    span_before = None
    span_after = None
    for span in spans:
        span_mid = (span.start + span.end) / 2.0
        if span_mid < seg_midpoint:
            if span_before is None or span_mid > ((span_before.start + span_before.end) / 2.0):
                span_before = span
        elif span_mid > seg_midpoint:
            if span_after is None or span_mid < ((span_after.start + span_after.end) / 2.0):
                span_after = span
    
    # Choose which span to use based on distance
    if span_before is not None and span_after is not None:
        dist_before = seg_midpoint - ((span_before.start + span_before.end) / 2.0)
        dist_after = ((span_after.start + span_after.end) / 2.0) - seg_midpoint
        chosen_span = span_before if dist_before <= dist_after else span_after
        logger.debug(
            "Segment at %.2f-%.2f (gap fallback): closer speaker %s (dist=%.2f vs %.2f)",
            seg.start,
            seg.end,
            chosen_span.speaker,
            min(dist_before, dist_after),
            max(dist_before, dist_after),
        )
        return chosen_span.speaker
    elif span_before is not None:
        logger.debug(
            "Segment at %.2f-%.2f (gap fallback): preceding speaker %s (no after)",
            seg.start,
            seg.end,
            span_before.speaker,
        )
        return span_before.speaker
    elif span_after is not None:
        logger.debug(
            "Segment at %.2f-%.2f (gap fallback): following speaker %s (no before)",
            seg.start,
            seg.end,
            span_after.speaker,
        )
        return span_after.speaker
    else:
        # Fallback to any span (shouldn't happen if spans is not empty)
        logger.debug("Segment at %.2f-%.2f: using first diarization span", seg.start, seg.end)
        return spans[0].speaker


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
    
    # Log when we can't find matching source
    if best_overlap == 0:
        logger.debug(
            "Segment at %.2f-%.2f: no overlap with original segments; defaulting source to %s (originals: %s-%s)",
            seg.start,
            seg.end,
            best_source,
            originals[0].start_time if originals else "N/A",
            originals[-1].end_time if originals else "N/A",
        )
    
    return best_source


def _set_status(
    meeting_id: int,
    *,
    status: str,
    detail: str | None = None,
    progress_pct: int | None = None,
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
        if detail is not None:
            meeting.processed_detail = detail
        if progress_pct is not None:
            meeting.processed_progress_pct = progress_pct
        if started_at is not None:
            meeting.processed_started_at = started_at
        if finished_at is not None:
            meeting.processed_finished_at = finished_at
        if error is not None:
            meeting.processed_error = error
        if has_processed is not None:
            meeting.has_processed_transcript = has_processed
        db.commit()
    finally:
        db.close()


def _run_postprocess_job(meeting_id: int) -> None:
    started = datetime.utcnow()
    _set_status(meeting_id, status="running", detail="Initializing", progress_pct=0, started_at=started, finished_at=None, error=None)
    db = SessionLocal()
    extracted_audio_path: str | None = None
    try:
        meeting = (
            db.query(Meeting)
            .options(selectinload(Meeting.transcript_segments))
            .filter(Meeting.id == meeting_id)
            .first()
        )
        if not meeting:
            raise RuntimeError("Meeting not found")
        
        # Determine which audio file to use
        audio_path = meeting.audio_file_path
        if not audio_path:
            # No separate audio file, try to extract from video
            if not meeting.video_file_path:
                raise RuntimeError("No audio or video uploaded for this meeting yet.")
            logger.info("No audio file found; extracting from video meeting_id=%s video_path=%s", meeting_id, meeting.video_file_path)
            _set_status(meeting_id, status="running", detail="Extracting audio from video", progress_pct=5)
            extracted_audio_path = _extract_audio_from_video(meeting.video_file_path)
            audio_path = extracted_audio_path
            logger.info("Audio extraction completed; will use extracted audio for processing meeting_id=%s", meeting_id)

        _set_status(meeting_id, status="running", detail="Transcribing and cleaning audio", progress_pct=10)
        
        # Detect if mic is the primary audio source
        mic_count = sum(1 for seg in meeting.transcript_segments if _extract_source(seg.speaker_label) == "mic")
        system_count = sum(1 for seg in meeting.transcript_segments if _extract_source(seg.speaker_label) == "system")
        is_mic_primary = mic_count > system_count if (mic_count + system_count) > 0 else False
        logger.info(
            "Audio source distribution meeting_id=%s: mic=%d system=%d primary_is_mic=%s",
            meeting_id,
            mic_count,
            system_count,
            is_mic_primary,
        )
        
        raw_segments = _split_for_diarization(_load_raw_segments(audio_path, is_mic_primary=is_mic_primary))
        
        # ── NEW: deduplicate segments produced by the splitter ──────────────────────
        seen_segs: set[tuple[float, float, str]] = set()
        deduped: list[_RawSegment] = []
        for seg in raw_segments:
            key = (round(seg.start, 2), round(seg.end, 2), seg.text)
            if key not in seen_segs:
                seen_segs.add(key)
                deduped.append(seg)
        if len(deduped) < len(raw_segments):
            logger.warning(
                "Removed %d duplicate segments after splitting meeting_id=%s",
                len(raw_segments) - len(deduped),
                meeting_id,
            )
        raw_segments = deduped
        # ── END NEW ──────────────────────────────────────────────────────────────────
        
        # Consolidate highly repetitive segments (hallucination cleanup)
        raw_segments = _consolidate_repetitive_segments(raw_segments)
        
        # Check if stop was requested
        if should_stop_processing(meeting_id):
            raise RuntimeError("Processing stopped by user")
        
        raw_total_sec = sum(max(0.0, seg.end - seg.start) for seg in raw_segments)
        logger.info(
            "Post-process transcription prepared meeting_id=%s raw_segments=%s total_speech_sec=%.2f use_pyannote=%s",
            meeting_id,
            len(raw_segments),
            raw_total_sec,
            settings.postprocess_use_pyannote,
        )
        
        # Log first few segments for debugging - DETAILED
        for idx, seg in enumerate(raw_segments[:min(15, len(raw_segments))]):
            logger.info(
                "Raw segment[%d]: start=%.2f end=%.2f duration=%.2f text_len=%d text=%s...",
                idx,
                seg.start,
                seg.end,
                seg.end - seg.start,
                len(seg.text),
                seg.text[:80],
            )
        
        # Check for overlapping segments
        overlaps = []
        for i in range(len(raw_segments) - 1):
            curr = raw_segments[i]
            next_seg = raw_segments[i + 1]
            if next_seg.start < curr.end:
                overlaps.append((i, i + 1, curr.end - next_seg.start))
        
        if overlaps:
            logger.warning("Found %d segment overlaps:", len(overlaps))
            for i, j, overlap_dur in overlaps[:5]:
                logger.warning(
                    "  Segments[%d-%d] overlap by %.3f sec: [%.2f-%.2f] vs [%.2f-%.2f]",
                    i,
                    j,
                    overlap_dur,
                    raw_segments[i].start,
                    raw_segments[i].end,
                    raw_segments[j].start,
                    raw_segments[j].end,
                )
        if settings.postprocess_use_pyannote:
            try:
                forced_num = settings.postprocess_force_num_speakers or None
                
                # Check if stop was requested before starting diarization
                if should_stop_processing(meeting_id):
                    raise RuntimeError("Processing stopped by user")
                    
                logger.info(
                    "Diarization start meeting_id=%s model=%s token_set=%s forced_num=%s retry_multi=%s",
                    meeting_id,
                    settings.postprocess_pyannote_model,
                    bool(settings.postprocess_hf_token),
                    forced_num,
                    settings.postprocess_retry_multi_speaker,
                )
                _set_status(meeting_id, status="running", detail="Diarizing speakers (1st pass)", progress_pct=30)
                diarization = _diarize_pyannote_with_timeout(audio_path, num_speakers=forced_num, timeout_sec=settings.postprocess_diarization_timeout_sec)
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
                    _set_status(meeting_id, status="running", detail="Diarizing speakers (2nd pass)", progress_pct=50)
                    retry_spans = _diarize_pyannote_with_timeout(
                        audio_path,
                        min_speakers=settings.postprocess_retry_min_speakers,
                        max_speakers=settings.postprocess_retry_max_speakers,
                        num_speakers=forced_num,
                        timeout_sec=settings.postprocess_diarization_timeout_sec,
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
                
                # Log unique speaker labels from diarization
                unique_speakers_dia = {s.speaker for s in diarization}
                logger.info("Diarization unique speakers: %s", unique_speakers_dia)
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

        _set_status(meeting_id, status="running", detail="Finalizing results", progress_pct=80)
        
        # Check if stop was requested before finalizing
        if should_stop_processing(meeting_id):
            raise RuntimeError("Processing stopped by user")
        
        db.query(ProcessedTranscriptSegment).filter(ProcessedTranscriptSegment.meeting_id == meeting_id).delete()
        speaker_label_counts: dict[str, int] = {}
        speaker_char_counts: dict[str, int] = {}
        segment_assignments: list[tuple[str, str, str]] = []  # (speaker, source, text_preview)
        
        # Check for segments with identical timing (indicates splitting issue)
        timing_to_segments: dict[tuple[float, float], list[_RawSegment]] = {}
        text_to_timings: dict[str, list[tuple[float, float]]] = {}
        
        for seg in raw_segments:
            timing_key = (round(seg.start, 2), round(seg.end, 2))
            if timing_key not in timing_to_segments:
                timing_to_segments[timing_key] = []
            timing_to_segments[timing_key].append(seg)
            
            # Track text to timings
            text_norm = seg.text.strip()[:100]  # First 100 chars for comparison
            if text_norm not in text_to_timings:
                text_to_timings[text_norm] = []
            text_to_timings[text_norm].append(timing_key)
        
        # Log any segments with identical timing
        for timing, segs in timing_to_segments.items():
            if len(segs) > 1:
                logger.warning(
                    "Multiple segments with identical timing %.2f-%.2f: %d segments",
                    timing[0],
                    timing[1],
                    len(segs),
                )
                for i, seg in enumerate(segs):
                    logger.warning(
                        "  Segment %d: text=%s...",
                        i,
                        seg.text[:50],
                    )
        
        # Log any identical text that appears at different times
        for text, timings in text_to_timings.items():
            if len(timings) > 1:
                logger.warning(
                    "Same text appears at %d different timings: %s... timings=%s",
                    len(timings),
                    text[:50],
                    timings,
                )
        
        # Debug: log segment timing issues
        prev_end = 0.0
        for idx, seg in enumerate(raw_segments[:5]):  # Check first 5 for timing issues
            if seg.start < prev_end:
                logger.warning(
                    "Segment overlap detected at index %d: prev_end=%.2f seg.start=%.2f seg.end=%.2f",
                    idx,
                    prev_end,
                    seg.start,
                    seg.end,
                )
            prev_end = seg.end
        
        for seg in raw_segments:
            source_label = _source_for_segment(seg, meeting.transcript_segments)
            diarized_speaker = _label_for_segment(seg, diarization)
            final_label = f"{source_label}:{diarized_speaker}"
            speaker_label_counts[final_label] = speaker_label_counts.get(final_label, 0) + 1
            speaker_char_counts[final_label] = speaker_char_counts.get(final_label, 0) + len(seg.text)
            
            # Track first few for logging
            if len(segment_assignments) < 10:
                segment_assignments.append((final_label, diarized_speaker, seg.text[:50]))
            
            db.add(
                ProcessedTranscriptSegment(
                    meeting_id=meeting_id,
                    speaker_label=final_label,
                    start_time=seg.start,
                    end_time=seg.end,
                    text=seg.text,
                )
            )
        
        # Log first assignments
        logger.info("Post-processing first 10 segment assignments: %s", segment_assignments)
        
        # Log speaker distribution with warnings if severely imbalanced
        logger.info("Post-processing speaker distribution meeting_id=%s segments: %s", meeting_id, speaker_label_counts)
        logger.info("Post-processing speaker distribution meeting_id=%s characters: %s", meeting_id, speaker_char_counts)
        
        # Check for severely imbalanced distribution (one speaker has >80% of content)
        if speaker_char_counts and len(speaker_char_counts) > 1:
            total_chars = sum(speaker_char_counts.values())
            max_speaker = max(speaker_char_counts.items(), key=lambda x: x[1])
            max_pct = (max_speaker[1] / total_chars) * 100
            if max_pct > 80:
                logger.warning(
                    "Severely imbalanced speaker distribution meeting_id=%s: %s has %.1f%% of content",
                    meeting_id,
                    max_speaker[0],
                    max_pct,
                )
        meeting.processed_status = "done"
        meeting.processed_detail = "Complete"
        meeting.processed_progress_pct = 100
        meeting.processed_started_at = started
        meeting.processed_finished_at = datetime.utcnow()
        meeting.processed_error = None
        meeting.has_processed_transcript = len(raw_segments) > 0
        db.commit()
        
        logger.info(
            "Post-processing complete meeting_id=%s segments=%s speakers=%s",
            meeting_id,
            len(raw_segments),
            len(speaker_label_counts),
        )
        
        # Log final details for debugging
        if segment_assignments:
            logger.info("Post-processing segment assignments (first 10): %s", [f"{label}:{text[:30]}" for label, _, text in segment_assignments])
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
        # Clean up extracted audio if we created it
        if extracted_audio_path:
            try:
                extracted_path_obj = Path(extracted_audio_path)
                if extracted_path_obj.exists():
                    extracted_path_obj.unlink()
                    logger.info("Cleaned up extracted audio file meeting_id=%s path=%s", meeting_id, extracted_audio_path)
            except Exception as cleanup_exc:
                logger.warning("Failed to clean up extracted audio meeting_id=%s path=%s error=%s", meeting_id, extracted_audio_path, cleanup_exc)
        
        db.close()
        with _jobs_lock:
            _jobs_in_flight.discard(meeting_id)
            _job_futures.pop(meeting_id, None)
            _stop_requested.discard(meeting_id)  # Clean up stop signal


def enqueue_postprocess(meeting_id: int) -> bool:
    with _jobs_lock:
        if meeting_id in _jobs_in_flight:
            return False
        _jobs_in_flight.add(meeting_id)
    _set_status(meeting_id, status="queued", started_at=None, finished_at=None, error=None, has_processed=False)
    future = _executor.submit(_run_postprocess_job, meeting_id)
    with _jobs_lock:
        _job_futures[meeting_id] = future
    return True
