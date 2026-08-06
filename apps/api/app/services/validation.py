from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.core.enums import TrancheStatus
from app.core.money import ZERO, format_inr
from app.services.financials import calculate_project_financials


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    field: str | None = None


class DomainValidationError(ValueError):
    def __init__(self, issues: list[ValidationIssue]):
        self.issues = issues
        super().__init__("; ".join(issue.message for issue in issues))


def ensure_no_negative_money(record: Any, fields: list[str]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for field in fields:
        value = getattr(record, field)
        if value < ZERO:
            issues.append(ValidationIssue("negative_money", f"{field.replace('_', ' ').title()} cannot be negative.", field))
    return issues


def validate_project_code_unique(project: Any, existing_codes: set[str]) -> None:
    if project.project_code in existing_codes:
        raise DomainValidationError([ValidationIssue("duplicate_project_code", f"Project code {project.project_code} already exists.", "project_code")])


def validate_single_active_sanction(sanction: Any, sanctions: Sequence[Any]) -> None:
    if _state(sanction.status) != "approved":
        return
    active = [s for s in sanctions if s.project_id == sanction.project_id and _state(s.status) == "approved" and s.id != sanction.id]
    if active:
        raise DomainValidationError([ValidationIssue("multiple_active_sanctions", "This project already has an approved original funding sanction.", "status")])


def validate_tranche(
    tranche: Any,
    project_sanctions: Sequence[Any],
    project_revisions: Sequence[Any],
    project_tranches: Sequence[Any],
    *,
    allow_approved_above_requested: bool = False,
) -> None:
    issues: list[ValidationIssue] = []
    issues.extend(
        ensure_no_negative_money(
            tranche,
            ["requested_amount", "approved_amount", "disbursed_amount", "refund_amount", "utilized_amount"],
        )
    )
    sequence_matches = [t for t in project_tranches if t.sequence_number == tranche.sequence_number and t.id != tranche.id and _state(t.status) != TrancheStatus.CANCELLED.value]
    if sequence_matches:
        issues.append(ValidationIssue("duplicate_sequence", f"Tranche sequence {tranche.sequence_number} already exists for this project.", "sequence_number"))
    if tranche.approved_amount > tranche.requested_amount and not allow_approved_above_requested:
        issues.append(ValidationIssue("approved_above_requested", "Approved amount cannot exceed requested amount without a documented override.", "approved_amount"))
    if tranche.disbursed_amount > tranche.approved_amount:
        issues.append(ValidationIssue("disbursed_above_approved", "Disbursed amount cannot exceed approved amount.", "disbursed_amount"))
    if tranche.refund_amount > tranche.disbursed_amount:
        issues.append(ValidationIssue("refund_above_disbursed", "Refund amount cannot exceed this tranche's disbursed amount.", "refund_amount"))
    if tranche.utilized_amount > (tranche.disbursed_amount - tranche.refund_amount):
        issues.append(ValidationIssue("utilized_above_net", "Utilized amount cannot exceed this tranche's net disbursed amount.", "utilized_amount"))
    if _state(tranche.status) in {TrancheStatus.DISBURSED.value, TrancheStatus.RECONCILED.value, TrancheStatus.RECONCILIATION_PENDING.value}:
        if not tranche.actual_disbursement_date:
            issues.append(ValidationIssue("missing_payment_date", "A disbursed tranche requires an actual disbursement date.", "actual_disbursement_date"))
        if not tranche.payment_reference and (tranche.payment_mode or "").lower() not in {"cash", "adjustment"}:
            issues.append(ValidationIssue("missing_payment_reference", "A disbursed tranche requires a payment reference.", "payment_reference"))
    if tranche.payment_reference:
        duplicate_refs = [
            t
            for t in project_tranches
            if t.payment_reference == tranche.payment_reference and t.id != tranche.id and _state(t.status) != TrancheStatus.CANCELLED.value
        ]
        if duplicate_refs:
            issues.append(ValidationIssue("duplicate_payment_reference", f"Payment reference {tranche.payment_reference} is already used.", "payment_reference"))
    if _state(tranche.status) in {TrancheStatus.APPROVED.value, TrancheStatus.SCHEDULED.value, TrancheStatus.PARTIALLY_DISBURSED.value, TrancheStatus.DISBURSED.value}:
        other_tranches = [t for t in project_tranches if t.id != tranche.id]
        summary = calculate_project_financials(project_sanctions, project_revisions, other_tranches)
        over_by: Decimal = tranche.approved_amount - summary.available_sanctioned_balance
        if over_by > ZERO:
            issues.append(
                ValidationIssue(
                    "approval_exceeds_sanction",
                    f"This tranche exceeds the project's available sanctioned balance by {format_inr(over_by)}.",
                    "approved_amount",
                )
            )
    if issues:
        raise DomainValidationError(issues)


def _state(value: Any) -> str:
    raw = getattr(value, "value", value)
    return str(raw)
