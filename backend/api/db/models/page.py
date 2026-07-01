"""ORM model for pages (one per PDF page)."""

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db.base import Base


class Page(Base):
    """A single page of a document. PK is the natural ``(document_id, page_number)``."""

    __tablename__ = "pages"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        primary_key=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, primary_key=True)  # 1-indexed

    raw_text: Mapped[str] = mapped_column(Text)
    was_ocr_applied: Mapped[bool] = mapped_column(Boolean)
    confidence: Mapped[float | None] = mapped_column(Float, default=None)
    width_pt: Mapped[float] = mapped_column(Float)
    height_pt: Mapped[float] = mapped_column(Float)

    document: Mapped["DocumentRow"] = relationship(back_populates="pages")
    blocks: Mapped[list["Block"]] = relationship(
        back_populates="page",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Block.block_id",
    )
