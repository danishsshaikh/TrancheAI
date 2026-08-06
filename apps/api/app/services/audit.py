from __future__ import annotations

from app.services.domain import AuditEvent


class AuditRecorder:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def record(self, event: AuditEvent) -> AuditEvent:
        forbidden = {"password", "api_key", "secret", "token"}
        event.previous_values = {k: v for k, v in event.previous_values.items() if k.lower() not in forbidden}
        event.new_values = {k: v for k, v in event.new_values.items() if k.lower() not in forbidden}
        self.events.append(event)
        return event

