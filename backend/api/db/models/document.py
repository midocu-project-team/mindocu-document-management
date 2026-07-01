"""ORM model for documents + the processing-status enum.

One row per uploaded PDF. The processed pipeline output lives in the related
``pages``/``blocks``/``segments`` tables (no JSONB blob); this row holds the
document-level metadata and the processing lifecycle.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db.base import Base


class ProcessingStatus(enum.StrEnum):
    """Lifecycle of a document; doubles as the current pipeline stage."""

    PENDING = "pending"
    EXTRACTING = "extracting"
    SEGMENTING = "segmenting"
    ENRICHING = "enriching"
    DONE = "done"
    FAILED = "failed"


class DocumentRow(Base):
    """One uploaded PDF: metadata columns + relations to the processed output."""

    __tablename__ = "documents"

    # PK comes from the pipeline domain (UUID), assigned at upload time.
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), index=True
    )

    file_name: Mapped[str] = mapped_column(String)
    file_size_bytes: Mapped[int] = mapped_column()
    total_pages: Mapped[int] = mapped_column(default=0)
    ocr_engine: Mapped[str | None] = mapped_column(String, default=None)
    pdf_path: Mapped[str] = mapped_column(String)

    # Stored as VARCHAR (native_enum=False) so new statuses need no ALTER TYPE.
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        SQLEnum(ProcessingStatus, native_enum=False, length=20),
        default=ProcessingStatus.PENDING,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, default=None)

    # Pipeline metadata; null until the job completes (row is `pending` first).
    enrichment_method: Mapped[str | None] = mapped_column(String, default=None)
    extracted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    enriched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    case: Mapped["Case"] = relationship(back_populates="documents")
    pages: Mapped[list["Page"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Page.page_number",
    )
    segments: Mapped[list["Segment"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Segment.start_page",
    )
