from __future__ import annotations

from typing import Protocol

from app.speech.schemas import SpeechTranscript


class STTProvider(Protocol):
    def transcribe(self, audio: bytes, content_type: str) -> SpeechTranscript:
        """Transcribe audio. Providers must not write project data."""


class FakeSTTProvider:
    def __init__(self, transcript: SpeechTranscript | None = None) -> None:
        self.transcript = transcript or SpeechTranscript(original_transcript="प्रकल्प दाखवा", detected_language="mr-IN")

    def transcribe(self, audio: bytes, content_type: str) -> SpeechTranscript:
        return self.transcript

