from __future__ import annotations

from app.ai.schemas import ALLOWED_ACTIONS, WRITE_ACTIONS, AIProposal, AIProposalPreview
from app.services.permissions import Actor, can

ALLOWED_FIELD_UPDATES = {"expected_completion_date", "closure_notes", "remarks", "project_status", "funding_status"}


def validate_ai_proposal(proposal: AIProposal, actor: Actor) -> AIProposalPreview:
    errors: list[str] = []
    warnings: list[str] = []
    if proposal.action not in ALLOWED_ACTIONS:
        errors.append(f"Unknown AI action: {proposal.action}.")
    if proposal.action in WRITE_ACTIONS:
        if not proposal.requires_confirmation:
            errors.append("Write proposals must require confirmation.")
        if not can(actor, "write"):
            errors.append("You do not have permission to confirm write proposals.")
    if proposal.action == "propose_field_update":
        field = proposal.payload.get("field")
        if field not in ALLOWED_FIELD_UPDATES:
            errors.append(f"AI cannot update field {field!r}.")
    for forbidden in ("sql", "doctype", "method", "filesystem_path", "python"):
        if forbidden in proposal.payload:
            errors.append(f"AI proposal contains forbidden key: {forbidden}.")
    if proposal.confidence < 0.4:
        warnings.append("Low confidence proposal; review carefully before confirming.")
    return AIProposalPreview(proposal=proposal, allowed=not errors, warnings=warnings, errors=errors)

