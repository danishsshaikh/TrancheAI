"""add import review batches

Revision ID: 0002_import_batches
Revises: 0001_initial
Create Date: 2026-08-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_import_batches"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "import_batches",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("import_type", sa.String(64), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(128)),
        sa.Column("file_fingerprint", sa.String(128), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="previewed"),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invalid_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("existing_match_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("create_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("update_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("committed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(128)),
        sa.Column("committed_by", sa.String(128)),
        sa.Column("committed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_import_batches_created_by", "import_batches", ["created_by"])
    op.create_index("ix_import_batches_file_fingerprint", "import_batches", ["file_fingerprint"])
    op.create_index("ix_import_batches_status", "import_batches", ["status"])

    op.create_table(
        "import_rows",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("row_fingerprint", sa.String(128), nullable=False),
        sa.Column("raw_values", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("normalized_values", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(32), nullable=False, server_default="valid"),
        sa.Column("proposed_action", sa.String(32), nullable=False, server_default="create"),
        sa.Column("duplicate", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("entity_type", sa.String(64)),
        sa.Column("entity_id", sa.String(128)),
        sa.Column("existing_entity_id", sa.String(128)),
        sa.Column("errors", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("warnings", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("result", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.UniqueConstraint("batch_id", "row_number", name="uq_import_row_batch_number"),
    )
    op.create_index("ix_import_rows_batch_id", "import_rows", ["batch_id"])
    op.create_index("ix_import_rows_row_fingerprint", "import_rows", ["row_fingerprint"])
    op.create_index("ix_import_rows_status", "import_rows", ["status"])
    op.create_index("uq_committed_import_row_fingerprint", "import_rows", ["row_fingerprint"], unique=True, postgresql_where=sa.text("status = 'committed'"))


def downgrade() -> None:
    op.drop_index("uq_committed_import_row_fingerprint", table_name="import_rows")
    op.drop_index("ix_import_rows_status", table_name="import_rows")
    op.drop_index("ix_import_rows_row_fingerprint", table_name="import_rows")
    op.drop_index("ix_import_rows_batch_id", table_name="import_rows")
    op.drop_table("import_rows")
    op.drop_index("ix_import_batches_status", table_name="import_batches")
    op.drop_index("ix_import_batches_file_fingerprint", table_name="import_batches")
    op.drop_index("ix_import_batches_created_by", table_name="import_batches")
    op.drop_table("import_batches")
