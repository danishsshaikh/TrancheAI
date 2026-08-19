"""add ai proposal confirmation table

Revision ID: 0003_ai_proposals
Revises: 0002_import_batches
Create Date: 2026-08-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_ai_proposals"
down_revision = "0002_import_batches"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_proposals",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(96), nullable=False),
        sa.Column("arguments", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("target_entity_type", sa.String(64)),
        sa.Column("target_entity_id", sa.String(128)),
        sa.Column("current_values", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("proposed_values", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("validation_result", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending_confirmation"),
        sa.Column("provider", sa.String(64)),
        sa.Column("model", sa.String(255)),
        sa.Column("original_request", sa.Text(), nullable=False),
        sa.Column("message", sa.Text()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("executed_at", sa.DateTime(timezone=True)),
        sa.Column("result", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_ai_proposals_action", "ai_proposals", ["action"])
    op.create_index("ix_ai_proposals_status", "ai_proposals", ["status"])
    op.create_index("ix_ai_proposals_user_id", "ai_proposals", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_proposals_user_id", table_name="ai_proposals")
    op.drop_index("ix_ai_proposals_status", table_name="ai_proposals")
    op.drop_index("ix_ai_proposals_action", table_name="ai_proposals")
    op.drop_table("ai_proposals")
