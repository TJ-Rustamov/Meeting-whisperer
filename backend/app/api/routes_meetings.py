from __future__ import annotations

from datetime import datetime
import logging
import time
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.db.session import get_db
from app.models.meeting import Meeting
from app.schemas.meeting import MeetingCreate, MeetingOut, MeetingUpdate, ProcessedTranscriptOut, ProcessedTranscriptSegmentOut
from app.services.postprocess import enqueue_postprocess, reset_postprocess_job, cancel_postprocess_job

router = APIRouter(prefix="/meetings", tags=["meetings"])
logger = logging.getLogger(__name__)


@router.post("", response_model=MeetingOut)
def create_meeting(payload: MeetingCreate, db: Session = Depends(get_db)):
    title = payload.title or f"Meeting {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    meeting = Meeting(title=title, created_at=datetime.utcnow())
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    logger.info("Meeting created id=%s title=%s", meeting.id, meeting.title)
    return meeting


@router.get("", response_model=list[MeetingOut])
def list_meetings(db: Session = Depends(get_db)):
    meetings = (
        db.query(Meeting)
        .options(selectinload(Meeting.transcript_segments))
        .order_by(Meeting.created_at.desc(), Meeting.id.desc())
        .all()
    )
    logger.debug("Meetings listed count=%s", len(meetings))
    return meetings


@router.get("/{meeting_id}", response_model=MeetingOut)
def get_meeting(meeting_id: int, db: Session = Depends(get_db)):
    meeting = (
        db.query(Meeting)
        .options(selectinload(Meeting.transcript_segments))
        .filter(Meeting.id == meeting_id)
        .first()
    )
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    logger.debug("Meeting fetched id=%s segments=%s", meeting.id, len(meeting.transcript_segments))
    return meeting


@router.get("/{meeting_id}/processed-transcript", response_model=ProcessedTranscriptOut)
def get_processed_transcript(meeting_id: int, db: Session = Depends(get_db)):
    meeting = (
        db.query(Meeting)
        .options(selectinload(Meeting.processed_transcript_segments))
        .filter(Meeting.id == meeting_id)
        .first()
    )
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return ProcessedTranscriptOut(
        meeting_id=meeting.id,
        processed_status=meeting.processed_status,
        processed_started_at=meeting.processed_started_at,
        processed_finished_at=meeting.processed_finished_at,
        processed_error=meeting.processed_error,
        segments=[ProcessedTranscriptSegmentOut.model_validate(seg) for seg in meeting.processed_transcript_segments],
    )


@router.post("/{meeting_id}/process", response_model=MeetingOut)
def trigger_meeting_postprocess(meeting_id: int, db: Session = Depends(get_db)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if not meeting.audio_file_path:
        raise HTTPException(status_code=400, detail="Upload audio before processing.")
    if meeting.processed_status in {"queued", "running"}:
        raise HTTPException(status_code=409, detail="Processing already in progress.")

    enqueued = enqueue_postprocess(meeting_id)
    if not enqueued:
        raise HTTPException(status_code=409, detail="Processing already in progress.")
    db.refresh(meeting)
    logger.info("Post-processing queued meeting_id=%s", meeting_id)
    return meeting


@router.post("/{meeting_id}/process/restart", response_model=MeetingOut)
def restart_meeting_postprocess(meeting_id: int, db: Session = Depends(get_db)):
    meeting = db.query(Meeting).options(selectinload(Meeting.processed_transcript_segments)).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if not meeting.audio_file_path:
        raise HTTPException(status_code=400, detail="Upload audio before processing.")

    for segment in meeting.processed_transcript_segments:
        db.delete(segment)
    meeting.processed_status = "idle"
    meeting.processed_started_at = None
    meeting.processed_finished_at = None
    meeting.processed_error = None
    meeting.has_processed_transcript = False
    db.commit()

    reset_postprocess_job(meeting_id)
    time.sleep(0.1)
    
    enqueued = enqueue_postprocess(meeting_id)
    if not enqueued:
        raise HTTPException(status_code=409, detail="Could not enqueue; another process may still be running.")
    db.refresh(meeting)
    logger.info("Post-processing restarted meeting_id=%s", meeting_id)
    return meeting


@router.post("/{meeting_id}/process/stop", response_model=MeetingOut)
def stop_meeting_postprocess(meeting_id: int, db: Session = Depends(get_db)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if meeting.processed_status not in {"queued", "running"}:
        raise HTTPException(status_code=409, detail="No processing in progress.")
    
    cancelled = cancel_postprocess_job(meeting_id)
    db.refresh(meeting)
    logger.info("Post-processing stop requested meeting_id=%s cancelled=%s", meeting_id, cancelled)
    return meeting


@router.delete("/{meeting_id}")
def delete_meeting(meeting_id: int, db: Session = Depends(get_db)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if meeting.audio_file_path:
        audio_path = Path(meeting.audio_file_path)
        if audio_path.exists():
            audio_path.unlink(missing_ok=True)
    if meeting.video_file_path:
        video_path = Path(meeting.video_file_path)
        if video_path.exists():
            video_path.unlink(missing_ok=True)
    db.delete(meeting)
    db.commit()
    logger.info("Meeting deleted id=%s", meeting_id)
    return {"ok": True}


@router.patch("/{meeting_id}", response_model=MeetingOut)
def update_meeting(meeting_id: int, payload: MeetingUpdate, db: Session = Depends(get_db)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    next_title = payload.title.strip()
    if not next_title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    meeting.title = next_title
    db.commit()
    db.refresh(meeting)
    logger.info("Meeting renamed id=%s title=%s", meeting_id, meeting.title)
    return meeting


@router.post("/{meeting_id}/audio", response_model=MeetingOut)
async def upload_meeting_audio(meeting_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    suffix = Path(file.filename or "recording.webm").suffix or ".webm"
    target = settings.audio_dir / f"meeting_{meeting_id}_{int(datetime.utcnow().timestamp())}{suffix}"
    content = await file.read()
    target.write_bytes(content)
    logger.info(
        "Audio uploaded meeting_id=%s bytes=%s path=%s",
        meeting_id,
        len(content),
        target.name,
    )

    meeting.audio_file_path = str(target)
    meeting.audio_url = f"/media/{target.name}"

    if meeting.transcript_segments:
        meeting.duration_seconds = max(seg.end_time for seg in meeting.transcript_segments)

    db.commit()
    db.refresh(meeting)
    return meeting


@router.post("/{meeting_id}/video", response_model=MeetingOut)
async def upload_meeting_video(meeting_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    suffix = Path(file.filename or "screen.webm").suffix or ".webm"
    target = settings.audio_dir / f"meeting_{meeting_id}_screen_{int(datetime.utcnow().timestamp())}{suffix}"
    content = await file.read()
    target.write_bytes(content)
    logger.info(
        "Video uploaded meeting_id=%s bytes=%s path=%s",
        meeting_id,
        len(content),
        target.name,
    )

    meeting.video_file_path = str(target)
    meeting.video_url = f"/media/{target.name}"
    db.commit()
    db.refresh(meeting)
    return meeting
