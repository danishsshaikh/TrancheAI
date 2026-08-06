from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class AuditEvent:
    id: str = field(default_factory=lambda: str(uuid4()))
    entity_type: str = ""
    entity_id: str = ""
    action: str = ""
    actor_id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    previous_values: dict[str, Any] = field(default_factory=dict)
    new_values: dict[str, Any] = field(default_factory=dict)
    reason: str | None = None
    source: str = "system"
    request_id: str | None = None


class AuditRecorder:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def record(self, event: AuditEvent) -> AuditEvent:
        forbidden = {"password", "api_key", "secret", "token"}
        event.previous_values = {k: v for k, v in event.previous_values.items() if k.lower() not in forbidden}
        event.new_values = {k: v for k, v in event.new_values.items() if k.lower() not in forbidden}
        self.events.append(event)
        return event
