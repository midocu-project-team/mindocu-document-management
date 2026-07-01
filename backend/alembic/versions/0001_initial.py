"""initial relational schema

One table per pipeline entity (cases, documents, pages, blocks, segments,
summary_references, reference_blocks) with natural composite keys for
pages/blocks and a surrogate bigint id for summary_references. Replaces the
earlier single-JSONB-blob layout (data was disposable, test environment).

Revision ID: 0001
Revises:
Create Date: 2026-07-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "documents",
        sa.Column("document_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_name", sa.String(), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("total_pages", sa.Integer(), nullable=False),
        sa.Column("ocr_engine", sa.String(), nullable=True),
        sa.Column("pdf_path", sa.String(), nullable=False),
        sa.Column("processing_status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("enrichment_method", sa.String(), nullable=True),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enriched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_documents_case_id", "documents", ["case_id"])
    op.create_index("ix_documents_processing_status", "documents", ["processing_status"])

    op.create_table(
        "pages",
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.document_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("page_number", sa.Integer(), primary_key=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("was_ocr_applied", sa.Boolean(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("width_pt", sa.Float(), nullable=False),
        sa.Column("height_pt", sa.Float(), nullable=False),
    )

    op.create_table(
        "blocks",
        sa.Column("document_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("block_id", sa.Integer(), primary_key=True),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("block_type", sa.String(length=20), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("bbox_x0", sa.Float(), nullable=True),
        sa.Column("bbox_y0", sa.Float(), nullable=True),
        sa.Column("bbox_x1", sa.Float(), nullable=True),
        sa.Column("bbox_y1", sa.Float(), nullable=True),
        sa.Column("source_ref", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["document_id", "page_number"],
            ["pages.document_id", "pages.page_number"],
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "(bbox_x0 IS NULL) = (bbox_y0 IS NULL) "
            "AND (bbox_x0 IS NULL) = (bbox_x1 IS NULL) "
            "AND (bbox_x0 IS NULL) = (bbox_y1 IS NULL)",
            name="ck_blocks_bbox_all_or_nothing",
        ),
    )

    op.create_table(
        "segments",
        sa.Column("segment_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.document_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("start_page", sa.Integer(), nullable=False),
        sa.Column("end_page", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("relevance", sa.Boolean(), nullable=False),
        sa.Column(
            "matched_keywords",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column("summary", sa.Text(), nullable=True),
    )
    op.create_index("ix_segments_document_id", "segments", ["document_id"])

    op.create_table(
        "summary_references",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "segment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("segments.segment_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "segment_id", "seq", name="uq_summary_references_segment_seq"
        ),
    )
    op.create_index(
        "ix_summary_references_segment_id", "summary_references", ["segment_id"]
    )

    op.create_table(
        "reference_blocks",
        sa.Column(
            "reference_id",
            sa.BigInteger(),
            sa.ForeignKey("summary_references.id", ondelete="CASCADE"),
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
    op.drop_table("reference_blocks")
    op.drop_index("ix_summary_references_segment_id", table_name="summary_references")
    op.drop_table("summary_references")
    op.drop_index("ix_segments_document_id", table_name="segments")
    op.drop_table("segments")
    op.drop_table("blocks")
    op.drop_table("pages")
    op.drop_index("ix_documents_processing_status", table_name="documents")
    op.drop_index("ix_documents_case_id", table_name="documents")
    op.drop_table("documents")
    op.drop_table("cases")
