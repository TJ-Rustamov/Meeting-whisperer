from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AppSettings(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    llm_provider: Mapped[str] = mapped_column(String(32), default="gemini", nullable=False)
    llm_api_key: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    profile_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    profile_email: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    profile_avatar_url: Mapped[str] = mapped_column(String(1024), default="", nullable=False)

