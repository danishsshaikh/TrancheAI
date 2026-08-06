from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    project_code: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=500)
    institution: str | None = None
    school: str | None = None
    department: str | None = None
    academic_year: str | None = None
    cohort: str | None = None
    project_status: str = "draft"
    funding_status: str = "not_sanctioned"
    start_date: date | None = None
    expected_completion_date: date | None = None
    remarks: str | None = None


class ProjectRead(ProjectCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    version: int


class SanctionCreate(BaseModel):
    sanction_reference: str
    sanction_date: date | None = None
    amount: Decimal = Decimal("0.00")
    funding_source: str | None = None
    financial_year: str | None = None
    status: str = "draft"
    remarks: str | None = None


class RevisionCreate(BaseModel):
    revision_number: int
    revision_type: str
    revision_date: date | None = None
    amount: Decimal = Decimal("0.00")
    status: str = "draft"
    reason: str | None = None


class TrancheCreate(BaseModel):
    sequence_number: int
    transaction_type: str = "advance"
    requested_amount: Decimal = Decimal("0.00")
    approved_amount: Decimal = Decimal("0.00")
    disbursed_amount: Decimal = Decimal("0.00")
    refund_amount: Decimal = Decimal("0.00")
    utilized_amount: Decimal = Decimal("0.00")
    request_date: date | None = None
    approval_date: date | None = None
    actual_disbursement_date: date | None = None
    payment_mode: str | None = None
    payment_reference: str | None = None
    status: str = "draft"
    remarks: str | None = None

