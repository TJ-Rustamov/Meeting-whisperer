from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TranscriptSegmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    speaker_label: str
    start_time: float
    end_time: float
    text: str


class ProcessedTranscriptSegmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    speaker_label: str
    start_time: float
    end_time: float
    text: str


class MeetingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime
    duration_seconds: float | None = None
    audio_url: str | None = None
    video_url: str | None = None
    summary_text: str | None = None
    processed_status: str = "idle"
    processed_started_at: datetime | None = None
    processed_finished_at: datetime | None = None
    processed_error: str | None = None
    has_processed_transcript: bool = False
    transcript_segments: list[TranscriptSegmentOut] = []


class ProcessedTranscriptOut(BaseModel):
    meeting_id: int
    processed_status: str
    processed_started_at: datetime | None = None
    processed_finished_at: datetime | None = None
    processed_error: str | None = None
    segments: list[ProcessedTranscriptSegmentOut] = []


class MeetingCreate(BaseModel):
    title: str | None = None


class MeetingUpdate(BaseModel):
    title: str
