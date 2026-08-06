from __future__ import annotations

from app.speech.provider import STTProvider
from app.speech.schemas import SpeechTranscript

SUPPORTED_AUDIO_TYPES = {"audio/wav", "audio/mpeg", "audio/mp4", "audio/webm"}
MAX_AUDIO_BYTES = 10 * 1024 * 1024


class SpeechService:
    def __init__(self, provider: STTProvider) -> None:
        self.provider = provider

    def transcribe(self, audio: bytes, content_type: str) -> SpeechTranscript:
        if content_type not in SUPPORTED_AUDIO_TYPES:
            raise ValueError(f"Unsupported audio type: {content_type}.")
        if len(audio) > MAX_AUDIO_BYTES:
            raise ValueError("Audio upload exceeds the 10 MB limit.")
        return self.provider.transcribe(audio, content_type)

