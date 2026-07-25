"""Server-side speech-to-text for browsers without the Web Speech API."""

from __future__ import annotations

from fastapi import APIRouter, File, UploadFile

from app.core.config import settings
from app.core.errors import ValidationFailure
from app.schemas.voice import TranscriptionResponse, VoiceCapabilities
from app.services import groq_client, transcription_service

router = APIRouter(prefix="/voice", tags=["voice"])


@router.get(
    "/capabilities",
    response_model=VoiceCapabilities,
    summary="What the server can transcribe",
)
def capabilities() -> VoiceCapabilities:
    return VoiceCapabilities(
        server_transcription=groq_client.is_configured(),
        engine=settings.STT_MODEL,
        accepted_formats=transcription_service.ACCEPTED_FORMATS,
        max_upload_bytes=settings.MAX_UPLOAD_BYTES,
    )


@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    summary="Transcribe a WAV recording",
)
async def transcribe(file: UploadFile = File(...)) -> TranscriptionResponse:
    audio = await file.read()
    if not audio:
        raise ValidationFailure("The uploaded file is empty.")
    if len(audio) > settings.MAX_UPLOAD_BYTES:
        raise ValidationFailure(
            f"That recording is larger than the "
            f"{settings.MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit."
        )

    text, engine, elapsed = transcription_service.transcribe(audio)
    return TranscriptionResponse(text=text, engine=engine, duration_ms=elapsed)
