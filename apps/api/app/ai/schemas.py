from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

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


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AIRequestPayload(StrictModel):
    text: str = Field(min_length=1, max_length=8000)
    current_project_id: str | None = None
    current_project_code: str | None = None
    language: str | None = None


class AIProviderEnvelope(StrictModel):
    kind: Literal["answer", "proposal", "clarification", "error"]
    message: str
    action: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = Field(default=None, ge=0, le=1)


class ProjectLookupArguments(StrictModel):
    project_code: str | None = None
    query: str | None = None


class SearchProjectsArguments(StrictModel):
    query: str
    limit: int = Field(default=10, ge=1, le=25)


class ReconciliationArguments(StrictModel):
    project_code: str | None = None
    only_open: bool = True


class ExportArguments(StrictModel):
    export_type: Literal["project_master", "tranche_register"]
    file_format: Literal["csv", "xlsx"] = "csv"


class CreateProjectArguments(StrictModel):
    project_code: str
    title: str
    institution: str | None = None
    school: str | None = None
    department: str | None = None
    academic_year: str | None = None
    cohort: str | None = None
    project_status: str = "draft"
    expected_completion_date: date | None = None
    remarks: str | None = None


class UpdateProjectArguments(StrictModel):
    project_code: str | None = None
    query: str | None = None
    updates: dict[str, Any]


class CreateTrancheArguments(StrictModel):
    project_code: str | None = None
    query: str | None = None
    sequence_number: int | None = None
    transaction_type: str = "advance"
    requested_amount: Any
    approved_amount: Any | None = None
    request_date: date | None = None
    remarks: str | None = None


class FundingRevisionArguments(StrictModel):
    project_code: str | None = None
    query: str | None = None
    revision_type: Literal["increase", "reduction"]
    amount: Any
    revision_date: date | None = None
    approval_reference: str | None = None
    reason: str | None = None


class TrancheActionArguments(StrictModel):
    project_code: str | None = None
    query: str | None = None
    tranche_id: str | None = None
    tranche_sequence: int | None = None
    amount: Any | None = None
    payment_reference: str | None = None
    payment_date: date | None = None
    payment_mode: str | None = None
    reason: str | None = None


class AIAssistantResponse(StrictModel):
    kind: Literal["answer", "proposal", "clarification", "error", "result", "export"]
    message: str
    proposal: dict[str, Any] | None = None
    data: dict[str, Any] | list[dict[str, Any]] | None = None
    download_url: str | None = None
