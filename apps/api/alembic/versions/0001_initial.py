"""initial trancheai schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("role", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_code", sa.String(96), nullable=False, unique=True),
        sa.Column("original_reference", sa.String(255)),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("short_title", sa.String(255)),
        sa.Column("description", sa.Text()),
        sa.Column("institution", sa.String(255)),
        sa.Column("school", sa.String(255)),
        sa.Column("department", sa.String(255)),
        sa.Column("academic_year", sa.String(32)),
        sa.Column("cohort", sa.String(64)),
        sa.Column("category", sa.String(128)),
        sa.Column("domain", sa.String(128)),
        sa.Column("technology_readiness_level", sa.String(64)),
        sa.Column("prototype_status", sa.String(128)),
        sa.Column("publication_status", sa.String(128)),
        sa.Column("patent_status", sa.String(128)),
        sa.Column("startup_status", sa.String(128)),
        sa.Column("project_status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("funding_status", sa.String(32), nullable=False, server_default="not_sanctioned"),
        sa.Column("start_date", sa.Date()),
        sa.Column("expected_completion_date", sa.Date()),
        sa.Column("actual_completion_date", sa.Date()),
        sa.Column("closure_notes", sa.Text()),
        sa.Column("remarks", sa.Text()),
        sa.Column("created_by", sa.String(128)),
        sa.Column("updated_by", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_projects_project_code", "projects", ["project_code"])
    op.create_index("ix_projects_school", "projects", ["school"])
    op.create_index("ix_projects_department", "projects", ["department"])
    op.create_index("ix_projects_academic_year", "projects", ["academic_year"])
    op.create_index("ix_projects_project_status", "projects", ["project_status"])
    op.create_table(
        "auth_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_table(
        "project_participants",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(64), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(64)),
        sa.Column("department", sa.String(255)),
        sa.Column("organization", sa.String(255)),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_project_participants_project_id", "project_participants", ["project_id"])
    op.create_table(
        "funding_sanctions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sanction_reference", sa.String(255), nullable=False),
        sa.Column("sanction_date", sa.Date()),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("funding_source", sa.String(255)),
        sa.Column("financial_year", sa.String(32)),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("approved_by", sa.String(128)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("remarks", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint("amount >= 0", name="ck_funding_sanction_amount_non_negative"),
    )
    op.create_index("ix_funding_sanctions_project_id", "funding_sanctions", ["project_id"])
    op.create_index("uq_one_approved_sanction_per_project", "funding_sanctions", ["project_id"], unique=True, postgresql_where=sa.text("status = 'approved'"))
    op.create_table(
        "funding_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("revision_type", sa.String(32), nullable=False),
        sa.Column("revision_date", sa.Date()),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("approval_reference", sa.String(255)),
        sa.Column("reason", sa.Text()),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("approved_by", sa.String(128)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("remarks", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("project_id", "revision_number", name="uq_project_revision_number"),
        sa.CheckConstraint("amount >= 0", name="ck_funding_revision_amount_non_negative"),
    )
    op.create_index("ix_funding_revisions_project_id", "funding_revisions", ["project_id"])
    op.create_table(
        "tranches",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("transaction_type", sa.String(32), nullable=False),
        sa.Column("purchase_order_number", sa.String(255)),
        sa.Column("purchase_order_received_date", sa.Date()),
        sa.Column("request_date", sa.Date()),
        sa.Column("requested_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("approved_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("approval_date", sa.Date()),
        sa.Column("expected_disbursement_date", sa.Date()),
        sa.Column("actual_disbursement_date", sa.Date()),
        sa.Column("disbursed_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("refund_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("utilized_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("payment_mode", sa.String(64)),
        sa.Column("payment_reference", sa.String(255)),
        sa.Column("bill_status", sa.String(64)),
        sa.Column("utilization_certificate_status", sa.String(64)),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("remarks", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("project_id", "sequence_number", name="uq_project_tranche_sequence"),
        sa.CheckConstraint("requested_amount >= 0", name="ck_tranche_requested_non_negative"),
        sa.CheckConstraint("approved_amount >= 0", name="ck_tranche_approved_non_negative"),
        sa.CheckConstraint("disbursed_amount >= 0", name="ck_tranche_disbursed_non_negative"),
        sa.CheckConstraint("refund_amount >= 0", name="ck_tranche_refund_non_negative"),
        sa.CheckConstraint("utilized_amount >= 0", name="ck_tranche_utilized_non_negative"),
    )
    op.create_index("ix_tranches_project_id", "tranches", ["project_id"])
    op.create_index("ix_tranches_status", "tranches", ["status"])
    op.create_index("ix_tranches_payment_reference", "tranches", ["payment_reference"])
    op.create_index("uq_active_payment_reference", "tranches", ["payment_reference"], unique=True, postgresql_where=sa.text("payment_reference IS NOT NULL"))
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(128), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("actor_id", sa.String(128)),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("previous_values", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("new_values", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("reason", sa.Text()),
        sa.Column("source", sa.String(64), nullable=False, server_default="api"),
        sa.Column("request_id", sa.String(128)),
    )
    op.create_index("ix_audit_events_entity", "audit_events", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_entity", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("uq_active_payment_reference", table_name="tranches")
    op.drop_index("ix_tranches_payment_reference", table_name="tranches")
    op.drop_index("ix_tranches_status", table_name="tranches")
    op.drop_index("ix_tranches_project_id", table_name="tranches")
    op.drop_table("tranches")
    op.drop_index("ix_funding_revisions_project_id", table_name="funding_revisions")
    op.drop_table("funding_revisions")
    op.drop_index("uq_one_approved_sanction_per_project", table_name="funding_sanctions")
    op.drop_index("ix_funding_sanctions_project_id", table_name="funding_sanctions")
    op.drop_table("funding_sanctions")
    op.drop_index("ix_project_participants_project_id", table_name="project_participants")
    op.drop_table("project_participants")
    op.drop_index("ix_auth_sessions_user_id", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_index("ix_projects_project_status", table_name="projects")
    op.drop_index("ix_projects_academic_year", table_name="projects")
    op.drop_index("ix_projects_department", table_name="projects")
    op.drop_index("ix_projects_school", table_name="projects")
    op.drop_index("ix_projects_project_code", table_name="projects")
    op.drop_table("projects")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
