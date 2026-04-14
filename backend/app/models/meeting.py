from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    audio_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    video_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_status: Mapped[str] = mapped_column(String(24), default="idle", nullable=False)
    processed_detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    processed_progress_pct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    processed_finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    processed_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    has_processed_transcript: Mapped[bool] = mapped_column(default=False, nullable=False)

    transcript_segments: Mapped[list["TranscriptSegment"]] = relationship(
        "TranscriptSegment", back_populates="meeting", cascade="all, delete-orphan", order_by="TranscriptSegment.id"
    )
    processed_transcript_segments: Mapped[list["ProcessedTranscriptSegment"]] = relationship(
        "ProcessedTranscriptSegment",
        back_populates="meeting",
        cascade="all, delete-orphan",
        order_by="ProcessedTranscriptSegment.id",
    )


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    speaker_label: Mapped[str] = mapped_column(String(64), default="speaker", nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    meeting: Mapped[Meeting] = relationship("Meeting", back_populates="transcript_segments")


class ProcessedTranscriptSegment(Base):
    __tablename__ = "processed_transcript_segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    speaker_label: Mapped[str] = mapped_column(String(64), default="speaker_1", nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    meeting: Mapped[Meeting] = relationship("Meeting", back_populates="processed_transcript_segments")
