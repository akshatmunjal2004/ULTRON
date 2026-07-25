"""Server-side speech-to-text with the Python SpeechRecognition library.

The browser's Web Speech API only exists in Chrome and Edge. This endpoint is
the fallback for everyone else: the frontend records a WAV and posts it here,
SpeechRecognition reads it into an AudioData, and Groq's Whisper model does the
transcription. Same API key, no extra service, no local model download.

If Groq is unavailable, it falls back to the free Google Web Speech endpoint,
which needs no key but is rate limited and unsuitable for production traffic.
"""

from __future__ import annotations

import io
import time
import wave

from app.core.errors import AppError, ValidationFailure
from app.core.logging import get_logger
from app.services import groq_client

logger = get_logger(__name__)

ACCEPTED_FORMATS = ["audio/wav", "audio/x-wav", "audio/wave", "audio/aiff", "audio/flac"]
MAX_SECONDS = 120


class TranscriptionError(AppError):
    status_code = 422
    code = "transcription_failed"
    message = "The audio could not be transcribed."


def _validate_wav(data: bytes) -> None:
    """Reject anything that is not a short, single-track PCM WAV."""
    try:
        with wave.open(io.BytesIO(data), "rb") as wav:
            frames = wav.getnframes()
            rate = wav.getframerate() or 1
            seconds = frames / rate
            channels = wav.getnchannels()
    except wave.Error as exc:
        raise ValidationFailure(
            "That file is not a readable WAV. Record with the app's recorder, "
            "or convert to 16-bit PCM WAV first."
        ) from exc

    if seconds > MAX_SECONDS:
        raise ValidationFailure(
            f"The clip is {seconds:.0f}s long. Keep it under {MAX_SECONDS}s."
        )
    if seconds < 0.2:
        raise ValidationFailure("That clip is too short to contain speech.")
    if channels > 2:
        raise ValidationFailure("Use mono or stereo audio.")


def transcribe(audio_bytes: bytes) -> tuple[str, str, int]:
    """Return (text, engine, duration_ms)."""
    import speech_recognition as sr

    _validate_wav(audio_bytes)
    started = time.perf_counter()

    recognizer = sr.Recognizer()
    with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
        audio = recognizer.record(source)

    engine = "groq-whisper"
    try:
        if not groq_client.is_configured():
            raise RuntimeError("Groq is not configured")
        from app.core.config import settings

        text = recognizer.recognize_groq(audio, model=settings.STT_MODEL)
    except Exception as exc:  # noqa: BLE001 - any failure means try the fallback
        logger.warning("Groq transcription failed (%s), falling back to Google", exc)
        engine = "google-web-speech"
        try:
            text = recognizer.recognize_google(audio)
        except sr.UnknownValueError as inner:
            raise TranscriptionError(
                "No speech was recognised in that clip."
            ) from inner
        except sr.RequestError as inner:
            raise TranscriptionError(
                "Both transcription services are unreachable. Check the server's "
                "network connection and GROQ_API_KEY."
            ) from inner

    elapsed = int((time.perf_counter() - started) * 1000)
    return (text or "").strip(), engine, elapsed
