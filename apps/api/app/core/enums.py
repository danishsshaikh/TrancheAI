from __future__ import annotations

from enum import StrEnum


class LabelledEnum(StrEnum):
    @property
    def label(self) -> str:
        return self.value.replace("_", " ").title()


class ProjectStatus(LabelledEnum):
    DRAFT = "draft"
    PROPOSED = "proposed"
    APPROVED = "approved"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class FundingStatus(LabelledEnum):
    NOT_SANCTIONED = "not_sanctioned"
    SANCTIONED = "sanctioned"
    PARTIALLY_DISBURSED = "partially_disbursed"
    FULLY_DISBURSED = "fully_disbursed"
    CLOSED = "closed"


class SanctionStatus(LabelledEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    SUPERSEDED = "superseded"
    CANCELLED = "cancelled"


class RevisionStatus(LabelledEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    CANCELLED = "cancelled"


class RevisionType(LabelledEnum):
    INCREASE = "increase"
    REDUCTION = "reduction"
    CORRECTION = "correction"
    TRANSFER = "transfer"
    OTHER = "other"


class TrancheStatus(LabelledEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PARTIALLY_DISBURSED = "partially_disbursed"
    DISBURSED = "disbursed"
    RECONCILIATION_PENDING = "reconciliation_pending"
    RECONCILED = "reconciled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class TransactionType(LabelledEnum):
    ADVANCE = "advance"
    REIMBURSEMENT = "reimbursement"
    DIRECT_PAYMENT = "direct_payment"
    PURCHASE_ORDER = "purchase_order"
    FINAL_SETTLEMENT = "final_settlement"
    OTHER = "other"


class Role(LabelledEnum):
    ADMINISTRATOR = "administrator"
    FUND_ADMINISTRATOR = "fund_administrator"
    FUND_REVIEWER = "fund_reviewer"
    AUDITOR = "auditor"
    VIEWER = "viewer"
