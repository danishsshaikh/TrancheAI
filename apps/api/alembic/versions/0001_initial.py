"""initial trancheai schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_code", sa.String(128), nullable=False, unique=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("project_status", sa.String(64), nullable=False, server_default="draft"),
        sa.Column("funding_status", sa.String(64), nullable=False, server_default="not_sanctioned"),
        sa.Column("institution", sa.String(255)),
        sa.Column("school", sa.String(255)),
        sa.Column("department", sa.String(255)),
        sa.Column("academic_year", sa.String(32)),
        sa.Column("cohort", sa.String(64)),
        sa.Column("remarks", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(128)),
        sa.Column("updated_by", sa.String(128)),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_projects_project_code", "projects", ["project_code"])
    op.create_table(
        "funding_sanctions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sanction_reference", sa.String(255), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("status", sa.String(64), nullable=False, server_default="draft"),
        sa.Column("sanction_date", sa.Date()),
        sa.Column("remarks", sa.Text()),
    )
    op.create_table(
        "funding_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("revision_type", sa.String(64), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("status", sa.String(64), nullable=False, server_default="draft"),
        sa.UniqueConstraint("project_id", "revision_number", name="uq_revision_project_number"),
    )
    op.create_table(
        "tranches",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("transaction_type", sa.String(64), nullable=False),
        sa.Column("requested_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("approved_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("disbursed_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("refund_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("utilized_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("actual_disbursement_date", sa.Date()),
        sa.Column("payment_reference", sa.String(255)),
        sa.Column("status", sa.String(64), nullable=False, server_default="draft"),
        sa.UniqueConstraint("project_id", "sequence_number", name="uq_tranche_project_sequence"),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("entity_type", sa.String(128), nullable=False),
        sa.Column("entity_id", sa.String(128), nullable=False),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("actor_id", sa.String(128)),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("previous_values", postgresql.JSONB(), nullable=False),
        sa.Column("new_values", postgresql.JSONB(), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("source", sa.String(64), nullable=False, server_default="system"),
        sa.Column("request_id", sa.String(128)),
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("tranches")
    op.drop_table("funding_revisions")
    op.drop_table("funding_sanctions")
    op.drop_index("ix_projects_project_code", table_name="projects")
    op.drop_table("projects")

