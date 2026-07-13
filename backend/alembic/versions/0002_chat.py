"""chat tables

Four tables for document chat (query-time, not a pipeline stage), mirroring
the segments/summary_references/reference_blocks shape 1:1: chat_sessions (one
per conversation, scoped to a document), chat_messages (one per turn),
chat_message_references (one per grounded sentence of an assistant message,
like summary_references) and chat_reference_blocks (the M:N grounding
junction, like reference_blocks).

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_sessions",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.document_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_chat_sessions_document_id", "chat_sessions", ["document_id"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.session_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("session_id", "seq", name="uq_chat_messages_session_seq"),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])

    op.create_table(
        "chat_message_references",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "message_id",
            sa.BigInteger(),
            sa.ForeignKey("chat_messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "message_id", "seq", name="uq_chat_message_references_message_seq"
        ),
    )
    op.create_index(
        "ix_chat_message_references_message_id",
        "chat_message_references",
        ["message_id"],
    )

    op.create_table(
        "chat_reference_blocks",
        sa.Column(
            "reference_id",
            sa.BigInteger(),
            sa.ForeignKey("chat_message_references.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("block_id", sa.Integer(), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id", "block_id"],
            ["blocks.document_id", "blocks.block_id"],
            ondelete="CASCADE",
        ),
    )


def downgrade() -> None:
    op.drop_table("chat_reference_blocks")
    op.drop_index(
        "ix_chat_message_references_message_id", table_name="chat_message_references"
    )
    op.drop_table("chat_message_references")
    op.drop_index("ix_chat_messages_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("ix_chat_sessions_document_id", table_name="chat_sessions")
    op.drop_table("chat_sessions")
