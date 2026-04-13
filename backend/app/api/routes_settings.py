from __future__ import annotations

import os
import threading

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.settings import AppSettings
from app.schemas.settings import SettingsInOut

router = APIRouter(prefix="/settings", tags=["settings"])


def _get_or_create_settings(db: Session) -> AppSettings:
    row = db.query(AppSettings).filter(AppSettings.id == 1).first()
    if row:
        return row
    row = AppSettings(id=1)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("", response_model=SettingsInOut)
def get_settings(db: Session = Depends(get_db)):
    row = _get_or_create_settings(db)
    return SettingsInOut(
        llmProvider=row.llm_provider,
        llmApiKey=row.llm_api_key,
        profile={
            "name": row.profile_name,
            "email": row.profile_email,
            "avatarUrl": row.profile_avatar_url,
        },
    )


@router.post("", response_model=SettingsInOut)
def save_settings(payload: SettingsInOut, db: Session = Depends(get_db)):
    row = _get_or_create_settings(db)
    row.llm_provider = payload.llmProvider
    row.llm_api_key = payload.llmApiKey
    row.profile_name = payload.profile.name
    row.profile_email = payload.profile.email
    row.profile_avatar_url = payload.profile.avatarUrl
    db.commit()
    return payload


@router.post("/shutdown")
def shutdown_app():
    # Delay process exit slightly so the HTTP response can flush.
    threading.Timer(0.25, lambda: os._exit(0)).start()
    return {"ok": True, "message": "Application shutdown requested"}
