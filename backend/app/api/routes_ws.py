from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketState

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.meeting import Meeting, TranscriptSegment
from app.services.transcriber import get_transcriber
from app.services.vad import HybridVAD, volume_tag_from_rms

router = APIRouter(tags=["ws"])
logger = logging.getLogger(__name__)


@dataclass
class StreamState:
    meeting_id: int
    source_label: str = "mixed"
    paused: bool = False
    stopped: bool = False
    utterance_buffer: bytearray = field(default_factory=bytearray)
    utterance_rms: list[int] = field(default_factory=list)
    utterance_start_sec: float = 0.0
    stream_time_sec: float = 0.0
    silence_sec: float = 0.0
    next_partial_at: float = 0.0
    last_partial_audio_sec: float = 0.0
    loop: asyncio.AbstractEventLoop | None = None
    frames_seen: int = 0
    bytes_received: int = 0
    carryover_buffer: bytearray = field(default_factory=bytearray)
    carryover_sec: float = 0.0


async def _run_transcribe(audio: bytes, boost_quality: bool = False) -> str:
    loop = asyncio.get_running_loop()
    transcriber = get_transcriber()
    return await loop.run_in_executor(None, lambda: transcriber.transcribe_pcm16(audio, boost_quality=boost_quality))


async def _emit_json(websocket: WebSocket, event: str, data: dict):
    await websocket.send_text(json.dumps({"event": event, **data}))


async def _safe_emit_json(websocket: WebSocket, event: str, data: dict) -> bool:
    # Starlette raises RuntimeError if we attempt to send after close.
    if websocket.application_state == WebSocketState.DISCONNECTED:
        return False
    try:
        await _emit_json(websocket, event, data)
        return True
    except RuntimeError:
        return False


async def _safe_close(websocket: WebSocket, code: int = 1000) -> None:
    if websocket.application_state == WebSocketState.DISCONNECTED:
        return
    try:
        await websocket.close(code=code)
    except RuntimeError:
        return


async def _finalize_utterance(websocket: WebSocket, state: StreamState, db: Session):
    if not state.utterance_buffer:
        return
    logger.info(
        "Finalizing utterance meeting_id=%s frames=%s bytes=%s stream_time=%.2fs",
        state.meeting_id,
        state.frames_seen,
        len(state.utterance_buffer),
        state.stream_time_sec,
    )
    boost_quality = state.source_label == "mic"
    text = (await _run_transcribe(bytes(state.utterance_buffer), boost_quality=boost_quality)).strip()
    end_time = state.stream_time_sec
    start_time = state.utterance_start_sec
    volume_tag = volume_tag_from_rms(state.utterance_rms)
    persisted_speaker_label = f"{state.source_label}:{volume_tag}"
    if text:
        segment = TranscriptSegment(
            meeting_id=state.meeting_id,
            speaker_label=persisted_speaker_label,
            start_time=start_time,
            end_time=end_time,
            text=text,
        )
        db.add(segment)
        db.commit()
        db.refresh(segment)
        await _safe_emit_json(
            websocket,
            "final_segment",
            {
                "id": segment.id,
                "meeting_id": segment.meeting_id,
                "speaker_label": segment.speaker_label,
                "source_label": state.source_label,
                "start_time": segment.start_time,
                "end_time": segment.end_time,
                "text": segment.text,
            },
        )
        logger.info(
            "Final segment emitted meeting_id=%s source=%s start=%.2fs end=%.2fs chars=%s speaker=%s",
            state.meeting_id,
            state.source_label,
            start_time,
            end_time,
            len(text),
            persisted_speaker_label,
        )
    else:
        logger.debug("Finalize produced empty text meeting_id=%s", state.meeting_id)
    overlap_bytes = min(
        len(state.utterance_buffer),
        int(settings.live_overlap_sec * settings.ws_sample_rate * 2),
    )
    if overlap_bytes > 0:
        state.carryover_buffer = bytearray(state.utterance_buffer[-overlap_bytes:])
        state.carryover_sec = overlap_bytes / 2 / settings.ws_sample_rate
    else:
        state.carryover_buffer.clear()
        state.carryover_sec = 0.0
    state.utterance_buffer.clear()
    state.utterance_rms.clear()
    state.silence_sec = 0.0
    state.last_partial_audio_sec = 0.0


@router.websocket("/ws/meetings/{meeting_id}/transcribe")
async def websocket_transcribe(websocket: WebSocket, meeting_id: int):
    source_label = (websocket.query_params.get("source") or "mixed").strip().lower()
    if source_label not in {"mixed", "mic", "system"}:
        source_label = "mixed"
    logger.info("WS connect requested for meeting_id=%s source=%s", meeting_id, source_label)
    await websocket.accept()
    db = SessionLocal()
    vad = HybridVAD()
    frame_bytes = vad.frame_bytes
    frame_sec = vad.frame_duration_sec
    carry = bytearray()
    state = StreamState(
        meeting_id=meeting_id,
        source_label=source_label,
        next_partial_at=time.monotonic() + settings.partial_interval_sec,
    )

    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        logger.warning("WS connect rejected, meeting not found: %s", meeting_id)
        await _safe_emit_json(websocket, "error", {"message": "Meeting not found"})
        await _safe_close(websocket, code=4404)
        db.close()
        return

    logger.info("WS opened for meeting_id=%s source=%s", meeting_id, source_label)
    await _safe_emit_json(websocket, "session_opened", {"meeting_id": meeting_id, "source_label": source_label})

    try:
        while not state.stopped:
            message = await websocket.receive()
            if "bytes" in message and message["bytes"] is not None:
                if state.paused:
                    continue
                chunk = message["bytes"]
                state.bytes_received += len(chunk)
                carry.extend(chunk)
                while len(carry) >= frame_bytes:
                    frame = bytes(carry[:frame_bytes])
                    del carry[:frame_bytes]
                    keep, voiced, rms = vad.process_frame(frame)
                    state.frames_seen += 1
                    state.stream_time_sec += frame_sec
                    if keep:
                        if not state.utterance_buffer:
                            state.utterance_start_sec = max(0.0, state.stream_time_sec - frame_sec - state.carryover_sec)
                            if state.carryover_buffer:
                                state.utterance_buffer.extend(state.carryover_buffer)
                                state.carryover_buffer.clear()
                                state.carryover_sec = 0.0
                        state.utterance_buffer.extend(frame)
                        state.utterance_rms.append(rms)
                        state.silence_sec = 0.0
                    else:
                        state.silence_sec += frame_sec
                    if not await _safe_emit_json(websocket, "vad_state", {"is_speech": voiced, "rms": rms}):
                        state.stopped = True
                        break
                    if state.frames_seen % settings.ws_debug_interval_frames == 0:
                        logger.info(
                            "WS frame meeting_id=%s source=%s frames=%s bytes_in=%s stream=%.2fs buffer=%s silence=%.2fs voiced=%s rms=%s",
                            meeting_id,
                            source_label,
                            state.frames_seen,
                            state.bytes_received,
                            state.stream_time_sec,
                            len(state.utterance_buffer),
                            state.silence_sec,
                            voiced,
                            rms,
                        )

                    now = time.monotonic()
                    if state.utterance_buffer and now >= state.next_partial_at:
                        current_audio_sec = len(state.utterance_buffer) / 2 / settings.ws_sample_rate
                        delta_audio_sec = current_audio_sec - state.last_partial_audio_sec
                        if delta_audio_sec < settings.partial_min_new_audio_sec:
                            state.next_partial_at = now + settings.partial_interval_sec
                            continue
                        max_partial_bytes = max(
                            frame_bytes,
                            int(settings.partial_max_audio_sec * settings.ws_sample_rate * 2),
                        )
                        partial_audio = bytes(state.utterance_buffer[-max_partial_bytes:])
                        boost_quality = state.source_label == "mic"
                        partial_text = (await _run_transcribe(partial_audio, boost_quality=boost_quality)).strip()
                        if partial_text:
                            if not await _safe_emit_json(
                                websocket,
                                "partial_transcript",
                                {
                                    "meeting_id": meeting_id,
                                    "source_label": source_label,
                                    "start_time": state.utterance_start_sec,
                                    "current_time": state.stream_time_sec,
                                    "speaker_label": f"{source_label}:{volume_tag_from_rms(state.utterance_rms)}",
                                    "text": partial_text,
                                },
                            ):
                                state.stopped = True
                                break
                            logger.info(
                                "Partial emitted meeting_id=%s source=%s start=%.2fs now=%.2fs chars=%s",
                                meeting_id,
                                source_label,
                                state.utterance_start_sec,
                                state.stream_time_sec,
                                len(partial_text),
                            )
                        state.last_partial_audio_sec = current_audio_sec
                        state.next_partial_at = now + settings.partial_interval_sec

                    current_utterance_sec = len(state.utterance_buffer) / 2 / settings.ws_sample_rate
                    if state.utterance_buffer and current_utterance_sec >= settings.ws_max_utterance_sec:
                        logger.info(
                            "Forcing finalize by max utterance window meeting_id=%s source=%s utterance=%.2fs",
                            meeting_id,
                            source_label,
                            current_utterance_sec,
                        )
                        await _finalize_utterance(websocket, state, db)

                    if state.utterance_buffer and state.silence_sec >= settings.silence_finalize_sec:
                        await _finalize_utterance(websocket, state, db)
            elif "text" in message and message["text"] is not None:
                try:
                    payload = json.loads(message["text"])
                except json.JSONDecodeError:
                    logger.warning("WS text frame is not valid JSON meeting_id=%s payload=%r", meeting_id, message["text"])
                    continue
                action = payload.get("action")
                logger.info("WS action=%s meeting_id=%s source=%s", action, meeting_id, source_label)
                if action == "pause":
                    state.paused = True
                elif action == "resume":
                    state.paused = False
                elif action == "stop":
                    state.stopped = True
                elif action == "start":
                    state.paused = False
                else:
                    logger.warning("WS unknown action=%s meeting_id=%s source=%s", action, meeting_id, source_label)
            elif message.get("type") == "websocket.disconnect":
                break

        await _finalize_utterance(websocket, state, db)
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if meeting:
            max_end = (
                db.query(TranscriptSegment.end_time)
                .filter(TranscriptSegment.meeting_id == meeting_id)
                .order_by(TranscriptSegment.end_time.desc())
                .first()
            )
            meeting.duration_seconds = float(max_end[0]) if max_end else 0.0
            db.commit()
        await _safe_emit_json(websocket, "session_closed", {"meeting_id": meeting_id, "source_label": source_label})
        logger.info("WS session closed cleanly for meeting_id=%s source=%s", meeting_id, source_label)
    except WebSocketDisconnect:
        logger.info("WS disconnected for meeting_id=%s source=%s", meeting_id, source_label)
        await _finalize_utterance(websocket, state, db)
    except Exception as exc:
        logger.exception("WS error meeting_id=%s source=%s: %s", meeting_id, source_label, exc)
        await _safe_emit_json(websocket, "error", {"message": str(exc)})
    finally:
        db.close()
        await _safe_close(websocket)
