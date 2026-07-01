"""ORM models for summary references and their block grounding (M:N).

A ``SummaryReference`` is one sentence of a segment's summary; ``seq`` keeps the
sentences ordered. ``ReferenceBlock`` is the junction table grounding a
reference in the blocks it was derived from (the future RAG hook).
"""

import uuid

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db.base import Base


class SummaryReference(Base):
    """One ordered sentence of a segment's summary. Surrogate bigint PK."""

    __tablename__ = "summary_references"
    __table_args__ = (
        UniqueConstraint("segment_id", "seq", name="uq_summary_references_segment_seq"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    segment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("segments.segment_id", ondelete="CASCADE"),
        index=True,
    )
    seq: Mapped[int] = mapped_column(Integer)  # 0-based order within the segment
    text: Mapped[str] = mapped_column(Text)

    segment: Mapped["Segment"] = relationship(back_populates="references")
    reference_blocks: Mapped[list["ReferenceBlock"]] = relationship(
        back_populates="reference",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ReferenceBlock.block_id",
    )


class ReferenceBlock(Base):
    """Junction: a reference grounded in a block. PK ``(reference_id, block_id)``.

    ``document_id`` is a non-key column carried only to form the composite FK to
    ``blocks`` (blocks are keyed by ``(document_id, block_id)``).
    """

    __tablename__ = "reference_blocks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["document_id", "block_id"],
            ["blocks.document_id", "blocks.block_id"],
            ondelete="CASCADE",
        ),
    )

    reference_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("summary_references.id", ondelete="CASCADE"),
        primary_key=True,
    )
    block_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))

    reference: Mapped["SummaryReference"] = relationship(back_populates="reference_blocks")
