from __future__ import annotations

from app.ai.action_validator import validate_ai_proposal
from app.ai.provider import AIProvider
from app.ai.schemas import AIProposalPreview
from app.services.audit import AuditEvent, AuditRecorder
from app.services.permissions import Actor, require


class AIProposalService:
    def __init__(self, provider: AIProvider, audit: AuditRecorder) -> None:
        self.provider = provider
        self.audit = audit

    def preview(self, request_text: str, actor: Actor) -> AIProposalPreview:
        require(actor, "read")
        proposal = self.provider.propose(request_text)
        preview = validate_ai_proposal(proposal, actor)
        self.audit.record(
            AuditEvent(
                entity_type="ai_proposal",
                entity_id="preview",
                action="preview",
                actor_id=actor.id,
                new_values={"action": proposal.action, "payload": proposal.payload, "allowed": preview.allowed},
                source="ai",
            )
        )
        return preview

    def confirm(self, preview: AIProposalPreview, actor: Actor) -> dict[str, str]:
        if not preview.allowed:
            raise ValueError("Cannot confirm an invalid AI proposal.")
        if preview.proposal.requires_confirmation:
            require(actor, "write")
        self.audit.record(
            AuditEvent(
                entity_type="ai_proposal",
                entity_id="confirmed",
                action="confirm",
                actor_id=actor.id,
                new_values={"action": preview.proposal.action, "payload": preview.proposal.payload},
                source="ai",
            )
        )
        return {"status": "accepted_for_domain_service", "action": preview.proposal.action}
