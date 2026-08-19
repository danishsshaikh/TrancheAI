from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class ProjectModel(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    project_code: Mapped[str] = mapped_column(String(96), unique=True, index=True, nullable=False)
    original_reference: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    short_title: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    institution: Mapped[str | None] = mapped_column(String(255))
    school: Mapped[str | None] = mapped_column(String(255), index=True)
    department: Mapped[str | None] = mapped_column(String(255), index=True)
    academic_year: Mapped[str | None] = mapped_column(String(32), index=True)
    cohort: Mapped[str | None] = mapped_column(String(64))
    category: Mapped[str | None] = mapped_column(String(128))
    domain: Mapped[str | None] = mapped_column(String(128))
    technology_readiness_level: Mapped[str | None] = mapped_column(String(64))
    prototype_status: Mapped[str | None] = mapped_column(String(128))
    publication_status: Mapped[str | None] = mapped_column(String(128))
    patent_status: Mapped[str | None] = mapped_column(String(128))
    startup_status: Mapped[str | None] = mapped_column(String(128))
    project_status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    funding_status: Mapped[str] = mapped_column(String(32), default="not_sanctioned", nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    expected_completion_date: Mapped[date | None] = mapped_column(Date)
    actual_completion_date: Mapped[date | None] = mapped_column(Date)
    closure_notes: Mapped[str | None] = mapped_column(Text)
    remarks: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(String(128))
    updated_by: Mapped[str | None] = mapped_column(String(128))

    participants: Mapped[list[ProjectParticipantModel]] = relationship(back_populates="project", cascade="all, delete-orphan")
    sanctions: Mapped[list[FundingSanctionModel]] = relationship(back_populates="project", cascade="all, delete-orphan")
    revisions: Mapped[list[FundingRevisionModel]] = relationship(back_populates="project", cascade="all, delete-orphan")
    tranches: Mapped[list[TrancheModel]] = relationship(back_populates="project", cascade="all, delete-orphan")


class UserModel(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AuthSessionModel(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProjectParticipantModel(TimestampMixin, Base):
    __tablename__ = "project_participants"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(64))
    department: Mapped[str | None] = mapped_column(String(255))
    organization: Mapped[str | None] = mapped_column(String(255))
    is_primary: Mapped[bool] = mapped_column(default=False, nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)

    project: Mapped[ProjectModel] = relationship(back_populates="participants")


class FundingSanctionModel(TimestampMixin, Base):
    __tablename__ = "funding_sanctions"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_funding_sanction_amount_non_negative"),
        Index("uq_one_approved_sanction_per_project", "project_id", unique=True, postgresql_where=text("status = 'approved'")),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    sanction_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    sanction_date: Mapped[date | None] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    funding_source: Mapped[str | None] = mapped_column(String(255))
    financial_year: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(128))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remarks: Mapped[str | None] = mapped_column(Text)

    project: Mapped[ProjectModel] = relationship(back_populates="sanctions")


class FundingRevisionModel(TimestampMixin, Base):
    __tablename__ = "funding_revisions"
    __table_args__ = (
        UniqueConstraint("project_id", "revision_number", name="uq_project_revision_number"),
        CheckConstraint("amount >= 0", name="ck_funding_revision_amount_non_negative"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    revision_type: Mapped[str] = mapped_column(String(32), nullable=False)
    revision_date: Mapped[date | None] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    approval_reference: Mapped[str | None] = mapped_column(String(255))
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(128))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remarks: Mapped[str | None] = mapped_column(Text)

    project: Mapped[ProjectModel] = relationship(back_populates="revisions")


class TrancheModel(TimestampMixin, Base):
    __tablename__ = "tranches"
    __table_args__ = (
        UniqueConstraint("project_id", "sequence_number", name="uq_project_tranche_sequence"),
        CheckConstraint("requested_amount >= 0", name="ck_tranche_requested_non_negative"),
        CheckConstraint("approved_amount >= 0", name="ck_tranche_approved_non_negative"),
        CheckConstraint("disbursed_amount >= 0", name="ck_tranche_disbursed_non_negative"),
        CheckConstraint("refund_amount >= 0", name="ck_tranche_refund_non_negative"),
        CheckConstraint("utilized_amount >= 0", name="ck_tranche_utilized_non_negative"),
        Index("uq_active_payment_reference", "payment_reference", unique=True, postgresql_where=text("payment_reference IS NOT NULL")),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(32), nullable=False)
    purchase_order_number: Mapped[str | None] = mapped_column(String(255))
    purchase_order_received_date: Mapped[date | None] = mapped_column(Date)
    request_date: Mapped[date | None] = mapped_column(Date)
    requested_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    approved_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    approval_date: Mapped[date | None] = mapped_column(Date)
    expected_disbursement_date: Mapped[date | None] = mapped_column(Date)
    actual_disbursement_date: Mapped[date | None] = mapped_column(Date)
    disbursed_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    refund_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    utilized_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    payment_mode: Mapped[str | None] = mapped_column(String(64))
    payment_reference: Mapped[str | None] = mapped_column(String(255), index=True)
    bill_status: Mapped[str | None] = mapped_column(String(64))
    utilization_certificate_status: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text)

    project: Mapped[ProjectModel] = relationship(back_populates="tranches")


class ImportBatchModel(TimestampMixin, Base):
    __tablename__ = "import_batches"
    __table_args__ = (
        Index("ix_import_batches_created_by", "created_by"),
        Index("ix_import_batches_status", "status"),
        Index("ix_import_batches_file_fingerprint", "file_fingerprint"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    import_type: Mapped[str] = mapped_column(String(64), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(128))
    file_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="previewed", nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    valid_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invalid_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    existing_match_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    create_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    update_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    committed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(128))
    committed_by: Mapped[str | None] = mapped_column(String(128))
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    rows: Mapped[list[ImportRowModel]] = relationship(back_populates="batch", cascade="all, delete-orphan")


class ImportRowModel(Base):
    __tablename__ = "import_rows"
    __table_args__ = (
        UniqueConstraint("batch_id", "row_number", name="uq_import_row_batch_number"),
        Index("ix_import_rows_batch_id", "batch_id"),
        Index("ix_import_rows_row_fingerprint", "row_fingerprint"),
        Index("ix_import_rows_status", "status"),
        Index("uq_committed_import_row_fingerprint", "row_fingerprint", unique=True, postgresql_where=text("status = 'committed'")),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    row_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    raw_values: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    normalized_values: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="valid", nullable=False)
    proposed_action: Mapped[str] = mapped_column(String(32), default="create", nullable=False)
    duplicate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(128))
    existing_entity_id: Mapped[str | None] = mapped_column(String(128))
    errors: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    warnings: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    result: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    batch: Mapped[ImportBatchModel] = relationship(back_populates="rows")


class AuditEventModel(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(128))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    previous_values: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    new_values: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(128))
