from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

AllowedAction = Literal[
    "search_projects",
    "summarize_project_funding",
    "list_pending_tranches",
    "explain_reconciliation",
    "propose_project_creation",
    "propose_tranche_creation",
    "propose_funding_revision",
    "propose_field_update",
    "request_export",
]


@dataclass(frozen=True)
class AIProposal:
    action: str
    payload: dict[str, Any]
    confidence: float = 0.0
    requires_confirmation: bool = True
    provider: str = "fake"
    model: str | None = None


@dataclass(frozen=True)
class AIProposalPreview:
    proposal: AIProposal
    allowed: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    financial_impact: dict[str, str] = field(default_factory=dict)


ALLOWED_ACTIONS: set[str] = {
    "search_projects",
    "summarize_project_funding",
    "list_pending_tranches",
    "explain_reconciliation",
    "propose_project_creation",
    "propose_tranche_creation",
    "propose_funding_revision",
    "propose_field_update",
    "request_export",
}
WRITE_ACTIONS = {"propose_project_creation", "propose_tranche_creation", "propose_funding_revision", "propose_field_update"}

