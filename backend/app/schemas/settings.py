from __future__ import annotations

from pydantic import BaseModel


class ProfileInOut(BaseModel):
    name: str = ""
    email: str = ""
    avatarUrl: str = ""


class SettingsInOut(BaseModel):
    llmProvider: str = "gemini"
    llmApiKey: str = ""
    profile: ProfileInOut = ProfileInOut()

