"""ORM models: ``cases`` and ``documents``. No separate segment table.

The full ``Document`` is stored as JSONB in ``documents.content``; the
metadata columns are denormalized copies, queryable without unpacking the
JSONB and populated already at upload time (when ``content`` is still null).
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db.base import Base
from pipeline import CURRENT_SCHEMA_VERSION


class ProcessingStatus(enum.StrEnum):
    """Lifecycle of a document; doubles as the current pipeline stage."""

    PENDING = "pending"
    EXTRACTING = "extracting"
    SEGMENTING = "segmenting"
    ENRICHING = "enriching"
    DONE = "done"
    FAILED = "failed"


class Case(Base):
    """A case file (Akte) grouping up to a few uploaded PDF documents."""

    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    documents: Mapped[list["DocumentRow"]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="DocumentRow.created_at",
    )


class DocumentRow(Base):
    """One uploaded PDF: metadata columns + the full Document as JSONB."""

    __tablename__ = "documents"

    # PK comes from the pipeline domain (str UUID), assigned at upload time.
    document_id: Mapped[str] = mapped_column(String, primary_key=True)
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), index=True
    )

    # Denormalized metadata (also present inside `content` once processed).
    file_name: Mapped[str] = mapped_column(String)
    file_size_bytes: Mapped[int] = mapped_column()
    total_pages: Mapped[int] = mapped_column(default=0)
    ocr_engine: Mapped[str | None] = mapped_column(String, default=None)
    schema_version: Mapped[int] = mapped_column(default=CURRENT_SCHEMA_VERSION)
    pdf_path: Mapped[str] = mapped_column(String)

    # Stored as VARCHAR (native_enum=False) so new statuses need no ALTER TYPE.
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        SQLEnum(ProcessingStatus, native_enum=False, length=20),
        default=ProcessingStatus.PENDING,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, default=None)

    # The serialized Document; null until the pipeline job completes. Segments
    # are stored without their pages/raw_text (those live in content["pages"]).
    content: Mapped[dict | None] = mapped_column(JSONB, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    case: Mapped["Case"] = relationship(back_populates="documents")
