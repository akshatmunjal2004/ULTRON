"""Speech-to-text contracts."""

from __future__ import annotations

from pydantic import BaseModel


class TranscriptionResponse(BaseModel):
    text: str
    engine: str
    duration_ms: int


class VoiceCapabilities(BaseModel):
    server_transcription: bool
    engine: str
    accepted_formats: list[str]
    max_upload_bytes: int
