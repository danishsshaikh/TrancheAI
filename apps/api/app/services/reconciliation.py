from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.core.enums import ProjectStatus, SanctionStatus, TrancheStatus
from app.core.money import ZERO, format_inr
from app.services.domain import FundingRevision, FundingSanction, Project, Tranche
from app.services.financials import calculate_project_financials


@dataclass(frozen=True)
class ReconciliationIssue:
    issue_type: str
    severity: str
    project_id: str
    description: str
    financial_impact: Decimal = ZERO
    related_record_type: str | None = None
    related_record_id: str | None = None
    status: str = "open"
    suggested_action: str = ""


def reconcile_project(
    project: Project,
    sanctions: list[FundingSanction],
    revisions: list[FundingRevision],
    tranches: list[Tranche],
) -> list[ReconciliationIssue]:
    issues: list[ReconciliationIssue] = []
    summary = calculate_project_financials(sanctions, revisions, tranches)
    if not any(s.status == SanctionStatus.APPROVED for s in sanctions):
        issues.append(_issue(project, "missing_approved_sanction", "high", "Project has no approved funding sanction.", suggested="Approve or import the original sanction."))
    if summary.net_disbursed_amount > summary.total_sanctioned_amount:
        over = summary.net_disbursed_amount - summary.total_sanctioned_amount
        issues.append(_issue(project, "over_disbursed", "critical", f"Net disbursement exceeds sanctioned funding by {format_inr(over)}.", over, suggested="Review sanctions, reductions and disbursements."))
    if summary.total_utilized_amount > summary.net_disbursed_amount:
        over = summary.total_utilized_amount - summary.net_disbursed_amount
        issues.append(_issue(project, "over_utilized", "high", f"Utilization exceeds net disbursement by {format_inr(over)}.", over, suggested="Correct utilization records or missing disbursements."))
    payment_refs: dict[str, str] = {}
    sequences: dict[int, str] = {}
    active_tranches = [t for t in tranches if t.status not in {TrancheStatus.CANCELLED, TrancheStatus.REJECTED}]
    for tranche in active_tranches:
        if tranche.refund_amount > tranche.disbursed_amount:
            issues.append(_issue(project, "refund_above_disbursed", "high", "Refund exceeds disbursed amount on a tranche.", tranche.refund_amount - tranche.disbursed_amount, "tranche", tranche.id, "Correct refund or disbursement amount."))
        if tranche.payment_reference:
            if tranche.payment_reference in payment_refs:
                issues.append(_issue(project, "duplicate_payment_reference", "medium", f"Payment reference {tranche.payment_reference} is duplicated.", ZERO, "tranche", tranche.id, "Verify the bank or UTR reference."))
            payment_refs[tranche.payment_reference] = tranche.id
        if tranche.sequence_number in sequences:
            issues.append(_issue(project, "duplicate_tranche_sequence", "high", f"Tranche sequence {tranche.sequence_number} is duplicated.", ZERO, "tranche", tranche.id, "Renumber the duplicated tranche after review."))
        sequences[tranche.sequence_number] = tranche.id
        if tranche.status in {TrancheStatus.DISBURSED, TrancheStatus.RECONCILED, TrancheStatus.RECONCILIATION_PENDING}:
            if not tranche.actual_disbursement_date:
                issues.append(_issue(project, "missing_disbursement_date", "medium", "Disbursed tranche is missing a payment date.", ZERO, "tranche", tranche.id, "Record the actual disbursement date."))
            if not tranche.payment_reference:
                issues.append(_issue(project, "missing_payment_reference", "medium", "Disbursed tranche is missing a payment reference.", ZERO, "tranche", tranche.id, "Record the cheque, UTR or bank reference."))
    if active_tranches:
        expected = set(range(1, max(t.sequence_number for t in active_tranches) + 1))
        actual = {t.sequence_number for t in active_tranches}
        if expected != actual:
            missing = ", ".join(str(v) for v in sorted(expected - actual))
            issues.append(_issue(project, "missing_tranche_sequence", "medium", f"Tranche sequence has gaps: {missing}.", suggested="Confirm whether a tranche record is missing."))
    pending = [t for t in active_tranches if t.status in {TrancheStatus.SUBMITTED, TrancheStatus.UNDER_REVIEW, TrancheStatus.APPROVED, TrancheStatus.SCHEDULED}]
    if project.project_status == ProjectStatus.COMPLETED and pending:
        issues.append(_issue(project, "completed_project_pending_tranche", "medium", "Completed project still has pending tranche activity.", suggested="Close, cancel or reconcile pending tranches."))
    if project.project_status == ProjectStatus.CANCELLED and active_tranches:
        issues.append(_issue(project, "cancelled_project_active_transactions", "high", "Cancelled project has active financial transactions.", suggested="Cancel or reconcile related financial records."))
    return issues


def _issue(
    project: Project,
    issue_type: str,
    severity: str,
    description: str,
    impact: Decimal = ZERO,
    record_type: str | None = None,
    record_id: str | None = None,
    suggested: str = "",
) -> ReconciliationIssue:
    return ReconciliationIssue(issue_type, severity, project.id, description, impact, record_type, record_id, suggested_action=suggested)

