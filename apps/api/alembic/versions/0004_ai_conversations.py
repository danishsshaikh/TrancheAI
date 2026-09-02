"""add ai conversations and messages

Revision ID: 0004_ai_conversations
Revises: 0003_ai_proposals
Create Date: 2026-09-02
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_ai_conversations"
down_revision = "0003_ai_proposals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255)),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("projects.id", ondelete="SET NULL")),
        sa.Column("project_code", sa.String(96)),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_ai_conversations_archived", "ai_conversations", ["archived"])
    op.create_index("ix_ai_conversations_project_id", "ai_conversations", ["project_id"])
    op.create_index("ix_ai_conversations_user_id", "ai_conversations", ["user_id"])

    op.create_table(
        "ai_messages",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("ai_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("response_kind", sa.String(32)),
        sa.Column("action", sa.String(96)),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("proposal_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("ai_proposals.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ai_messages_conversation_id", "ai_messages", ["conversation_id"])
    op.create_index("ix_ai_messages_created_at", "ai_messages", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_ai_messages_created_at", table_name="ai_messages")
    op.drop_index("ix_ai_messages_conversation_id", table_name="ai_messages")
    op.drop_table("ai_messages")
    op.drop_index("ix_ai_conversations_user_id", table_name="ai_conversations")
    op.drop_index("ix_ai_conversations_project_id", table_name="ai_conversations")
    op.drop_index("ix_ai_conversations_archived", table_name="ai_conversations")
    op.drop_table("ai_conversations")
