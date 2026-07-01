"""ORM model for content blocks (one per ``ContentBlock``).

The bounding box is stored as four nullable float columns and mapped back to
the internal ``BoundingBox`` tuple in the repository. A CHECK keeps them
all-set or all-null (a block either has a bbox or it doesn't).
"""

import uuid

from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db.base import Base


class Block(Base):
    """A content block. PK is the natural ``(document_id, block_id)``.

    The only foreign key points at ``pages`` (composite), so the document is
    reached via the page -- there is no second, ambiguous FK path to documents.
    """

    __tablename__ = "blocks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["document_id", "page_number"],
            ["pages.document_id", "pages.page_number"],
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "(bbox_x0 IS NULL) = (bbox_y0 IS NULL) "
            "AND (bbox_x0 IS NULL) = (bbox_x1 IS NULL) "
            "AND (bbox_x0 IS NULL) = (bbox_y1 IS NULL)",
            name="ck_blocks_bbox_all_or_nothing",
        ),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    block_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    page_number: Mapped[int] = mapped_column(Integer)

    block_type: Mapped[str] = mapped_column(String(20))
    text: Mapped[str] = mapped_column(Text)
    bbox_x0: Mapped[float | None] = mapped_column(Float, default=None)
    bbox_y0: Mapped[float | None] = mapped_column(Float, default=None)
    bbox_x1: Mapped[float | None] = mapped_column(Float, default=None)
    bbox_y1: Mapped[float | None] = mapped_column(Float, default=None)
    source_ref: Mapped[str | None] = mapped_column(String, default=None)

    page: Mapped["Page"] = relationship(back_populates="blocks")
