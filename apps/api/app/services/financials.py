from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.core.enums import RevisionStatus, RevisionType, SanctionStatus, TrancheStatus
from app.core.money import ZERO
from app.services.domain import FundingRevision, FundingSanction, Tranche

REQUEST_TOTAL_STATES = {
    TrancheStatus.SUBMITTED,
    TrancheStatus.UNDER_REVIEW,
    TrancheStatus.APPROVED,
    TrancheStatus.SCHEDULED,
    TrancheStatus.PARTIALLY_DISBURSED,
    TrancheStatus.DISBURSED,
    TrancheStatus.RECONCILIATION_PENDING,
    TrancheStatus.RECONCILED,
}
APPROVED_TOTAL_STATES = {
    TrancheStatus.APPROVED,
    TrancheStatus.SCHEDULED,
    TrancheStatus.PARTIALLY_DISBURSED,
    TrancheStatus.DISBURSED,
    TrancheStatus.RECONCILIATION_PENDING,
    TrancheStatus.RECONCILED,
}
DISBURSED_TOTAL_STATES = {
    TrancheStatus.PARTIALLY_DISBURSED,
    TrancheStatus.DISBURSED,
    TrancheStatus.RECONCILIATION_PENDING,
    TrancheStatus.RECONCILED,
}


@dataclass(frozen=True)
class ProjectFinancialSummary:
    initial_sanctioned_amount: Decimal
    approved_funding_increases: Decimal
    approved_funding_reductions: Decimal
    total_sanctioned_amount: Decimal
    total_requested_amount: Decimal
    total_approved_tranche_amount: Decimal
    gross_disbursed_amount: Decimal
    total_refunded_amount: Decimal
    net_disbursed_amount: Decimal
    total_utilized_amount: Decimal
    available_sanctioned_balance: Decimal
    unutilized_disbursed_balance: Decimal
    pending_approved_amount: Decimal
    tranche_count: int
    latest_disbursement_date: date | None
    reconciliation_status: str


def calculate_project_financials(
    sanctions: list[FundingSanction],
    revisions: list[FundingRevision],
    tranches: list[Tranche],
) -> ProjectFinancialSummary:
    approved_sanctions = [s for s in sanctions if s.status == SanctionStatus.APPROVED]
    approved_revisions = [r for r in revisions if r.status == RevisionStatus.APPROVED]
    valid_requested = [t for t in tranches if t.status in REQUEST_TOTAL_STATES]
    valid_approved = [t for t in tranches if t.status in APPROVED_TOTAL_STATES]
    valid_disbursed = [t for t in tranches if t.status in DISBURSED_TOTAL_STATES]

    initial = sum((s.amount for s in approved_sanctions), ZERO)
    increases = sum((r.amount for r in approved_revisions if r.revision_type == RevisionType.INCREASE), ZERO)
    reductions = sum((r.amount for r in approved_revisions if r.revision_type == RevisionType.REDUCTION), ZERO)
    total_sanctioned = initial + increases - reductions
    requested = sum((t.requested_amount for t in valid_requested), ZERO)
    approved = sum((t.approved_amount for t in valid_approved), ZERO)
    gross_disbursed = sum((t.disbursed_amount for t in valid_disbursed), ZERO)
    refunded = sum((t.refund_amount for t in valid_disbursed), ZERO)
    net_disbursed = gross_disbursed - refunded
    utilized = sum((t.utilized_amount for t in valid_disbursed), ZERO)
    available = total_sanctioned - net_disbursed
    unutilized = net_disbursed - utilized
    pending = approved - gross_disbursed
    latest = max((t.actual_disbursement_date for t in valid_disbursed if t.actual_disbursement_date), default=None)
    status = _status(initial, total_sanctioned, net_disbursed, utilized, refunded, gross_disbursed)
    return ProjectFinancialSummary(
        initial_sanctioned_amount=initial,
        approved_funding_increases=increases,
        approved_funding_reductions=reductions,
        total_sanctioned_amount=total_sanctioned,
        total_requested_amount=requested,
        total_approved_tranche_amount=approved,
        gross_disbursed_amount=gross_disbursed,
        total_refunded_amount=refunded,
        net_disbursed_amount=net_disbursed,
        total_utilized_amount=utilized,
        available_sanctioned_balance=available,
        unutilized_disbursed_balance=unutilized,
        pending_approved_amount=pending,
        tranche_count=len([t for t in tranches if t.status not in {TrancheStatus.CANCELLED, TrancheStatus.REJECTED}]),
        latest_disbursement_date=latest,
        reconciliation_status=status,
    )


def _status(
    initial: Decimal,
    sanctioned: Decimal,
    net_disbursed: Decimal,
    utilized: Decimal,
    refunded: Decimal,
    gross_disbursed: Decimal,
) -> str:
    if initial == ZERO:
        return "missing_sanction"
    if refunded > gross_disbursed:
        return "refund_conflict"
    if net_disbursed > sanctioned:
        return "over_disbursed"
    if utilized > net_disbursed:
        return "over_utilized"
    if sanctioned < ZERO:
        return "attention_required"
    return "balanced"

