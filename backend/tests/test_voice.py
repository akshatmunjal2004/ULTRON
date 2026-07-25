import io
import math
import struct
import wave

import pytest

from app.services import transcription_service


def make_wav(seconds: float = 1.0, rate: int = 16000, channels: int = 1) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        frames = bytearray()
        for i in range(int(rate * seconds)):
            sample = int(12000 * math.sin(2 * math.pi * 220 * i / rate))
            frames += struct.pack("<h", sample) * channels
        wav.writeframes(bytes(frames))
    return buf.getvalue()


def test_capabilities_are_reported(client):
    res = client.get("/api/v1/voice/capabilities")
    assert res.status_code == 200
    assert "audio/wav" in res.json()["accepted_formats"]


def test_non_wav_upload_is_rejected(client):
    res = client.post(
        "/api/v1/voice/transcribe",
        files={"file": ("clip.wav", b"definitely not audio", "audio/wav")},
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "validation_failed"


def test_empty_upload_is_rejected(client):
    res = client.post(
        "/api/v1/voice/transcribe", files={"file": ("clip.wav", b"", "audio/wav")}
    )
    assert res.status_code == 422


def test_clip_that_is_too_short_is_rejected():
    from app.core.errors import ValidationFailure

    with pytest.raises(ValidationFailure):
        transcription_service._validate_wav(make_wav(seconds=0.05))


def test_clip_that_is_too_long_is_rejected():
    from app.core.errors import ValidationFailure

    with pytest.raises(ValidationFailure):
        transcription_service._validate_wav(make_wav(seconds=130, rate=8000))


def test_valid_wav_passes_validation():
    transcription_service._validate_wav(make_wav(seconds=1.0))


def test_transcription_falls_back_when_groq_is_unavailable(monkeypatch, client):
    calls = {}

    def fake_google(self, audio, **kwargs):
        calls["google"] = True
        return "hello world"

    import speech_recognition as sr

    monkeypatch.setattr(sr.Recognizer, "recognize_google", fake_google)
    monkeypatch.setattr(
        transcription_service.groq_client, "is_configured", lambda: False
    )

    res = client.post(
        "/api/v1/voice/transcribe",
        files={"file": ("clip.wav", make_wav(1.0), "audio/wav")},
    )
    assert res.status_code == 200
    assert res.json()["text"] == "hello world"
    assert res.json()["engine"] == "google-web-speech"
    assert calls["google"] is True
