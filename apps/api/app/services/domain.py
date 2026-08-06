from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from app.core.enums import (
    FundingStatus,
    ProjectStatus,
    RevisionStatus,
    RevisionType,
    SanctionStatus,
    TrancheStatus,
    TransactionType,
)
from app.core.money import ZERO, money


def new_id() -> str:
    return str(uuid4())


@dataclass
class ProjectParticipant:
    id: str = field(default_factory=new_id)
    project_id: str = ""
    role: str = "project_member"
    full_name: str = ""
    email: str | None = None
    phone: str | None = None
    department: str | None = None
    organization: str | None = None
    is_primary: bool = False
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None


@dataclass
class Project:
    id: str = field(default_factory=new_id)
    project_code: str = ""
    title: str = ""
    original_reference: str | None = None
    short_title: str | None = None
    description: str | None = None
    institution: str | None = None
    school: str | None = None
    department: str | None = None
    academic_year: str | None = None
    cohort: str | None = None
    category: str | None = None
    domain: str | None = None
    technology_readiness_level: str | None = None
    prototype_status: str | None = None
    publication_status: str | None = None
    patent_status: str | None = None
    startup_status: str | None = None
    project_status: ProjectStatus = ProjectStatus.DRAFT
    funding_status: FundingStatus = FundingStatus.NOT_SANCTIONED
    start_date: date | None = None
    expected_completion_date: date | None = None
    actual_completion_date: date | None = None
    closure_notes: str | None = None
    remarks: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str | None = None
    updated_by: str | None = None
    version: int = 1
    participants: list[ProjectParticipant] = field(default_factory=list)


@dataclass
class FundingSanction:
    id: str = field(default_factory=new_id)
    project_id: str = ""
    sanction_reference: str = ""
    sanction_date: date | None = None
    amount: Decimal = ZERO
    funding_source: str | None = None
    financial_year: str | None = None
    status: SanctionStatus = SanctionStatus.DRAFT
    approved_by: str | None = None
    approved_at: datetime | None = None
    remarks: str | None = None

    def __post_init__(self) -> None:
        self.amount = money(self.amount)


@dataclass
class FundingRevision:
    id: str = field(default_factory=new_id)
    project_id: str = ""
    revision_number: int = 1
    revision_type: RevisionType = RevisionType.INCREASE
    revision_date: date | None = None
    amount: Decimal = ZERO
    approval_reference: str | None = None
    reason: str | None = None
    status: RevisionStatus = RevisionStatus.DRAFT
    approved_by: str | None = None
    approved_at: datetime | None = None
    remarks: str | None = None

    def __post_init__(self) -> None:
        self.amount = money(self.amount)


@dataclass
class Tranche:
    id: str = field(default_factory=new_id)
    project_id: str = ""
    sequence_number: int = 1
    transaction_type: TransactionType = TransactionType.ADVANCE
    purchase_order_number: str | None = None
    purchase_order_received_date: date | None = None
    request_date: date | None = None
    requested_amount: Decimal = ZERO
    approved_amount: Decimal = ZERO
    approval_date: date | None = None
    expected_disbursement_date: date | None = None
    actual_disbursement_date: date | None = None
    disbursed_amount: Decimal = ZERO
    refund_amount: Decimal = ZERO
    utilized_amount: Decimal = ZERO
    payment_mode: str | None = None
    payment_reference: str | None = None
    bill_status: str | None = None
    utilization_certificate_status: str | None = None
    status: TrancheStatus = TrancheStatus.DRAFT
    remarks: str | None = None

    def __post_init__(self) -> None:
        self.requested_amount = money(self.requested_amount)
        self.approved_amount = money(self.approved_amount)
        self.disbursed_amount = money(self.disbursed_amount)
        self.refund_amount = money(self.refund_amount)
        self.utilized_amount = money(self.utilized_amount)


@dataclass
class AuditEvent:
    id: str = field(default_factory=new_id)
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
