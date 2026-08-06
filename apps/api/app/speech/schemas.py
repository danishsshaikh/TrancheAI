from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpeechTranscript:
    original_transcript: str
    detected_language: str
    edited_transcript: str | None = None
    translated_text: str | None = None

    @property
    def text_for_ai(self) -> str:
        return self.edited_transcript or self.original_transcript

