"""ORM model for enriched segments (one per ``EnrichedSegment``).

``summary`` is denormalized (write-once cache) for cheap list views; the source
of truth is the related ``summary_references``. ``matched_keywords`` records the
keywords behind the original, deterministic relevance decision.
"""

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db.base import Base


class Segment(Base):
    """A document segment with its stage-3 enrichment."""

    __tablename__ = "segments"

    segment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        index=True,
    )

    start_page: Mapped[int] = mapped_column(Integer)  # 1-indexed, inclusive
    end_page: Mapped[int] = mapped_column(Integer)  # 1-indexed, inclusive
    confidence: Mapped[float | None] = mapped_column(Float, default=None)
    title: Mapped[str | None] = mapped_column(String, default=None)
    relevance: Mapped[bool] = mapped_column(Boolean)
    matched_keywords: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}"
    )
    summary: Mapped[str | None] = mapped_column(Text, default=None)

    document: Mapped["DocumentRow"] = relationship(back_populates="segments")
    references: Mapped[list["SummaryReference"]] = relationship(
        back_populates="segment",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="SummaryReference.seq",
    )
