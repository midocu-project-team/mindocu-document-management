"""Data access for documents + the Pydantic<->row mapping.

The full ``Document`` is stored in ``content`` (JSONB) with the per-segment
``pages``/``raw_text`` stripped -- the pages live once at ``content["pages"]``.
On read they are reconstructed from the page range so the (validated)
``Document`` is whole again. ``schema_version`` is checked with an upcast hook
(identity for v1).
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.db.models import DocumentRow, ProcessingStatus
from api.exceptions import DocumentNotFoundError
from pipeline import CURRENT_SCHEMA_VERSION, Document


class DocumentRepository:
    """CRUD + (de)serialization between ``Document`` and ``DocumentRow``."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_pending(
        self,
        *,
        document_id: str,
        case_id: uuid.UUID,
        file_name: str,
        file_size_bytes: int,
        pdf_path: str,
    ) -> DocumentRow:
        """Inserts a `pending` row (no content yet) for a freshly uploaded PDF."""
        row = DocumentRow(
            document_id=document_id,
            case_id=case_id,
            file_name=file_name,
            file_size_bytes=file_size_bytes,
            pdf_path=pdf_path,
            processing_status=ProcessingStatus.PENDING,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def get(self, document_id: str) -> DocumentRow | None:
        return self.session.get(DocumentRow, document_id)

    def require(self, document_id: str) -> DocumentRow:
        row = self.get(document_id)
        if row is None:
            raise DocumentNotFoundError(document_id)
        return row

    def count_for_case(self, case_id: uuid.UUID) -> int:
        return self.session.scalar(
            select(func.count())
            .select_from(DocumentRow)
            .where(DocumentRow.case_id == case_id)
        )

    def set_status(
        self,
        document_id: str,
        status: ProcessingStatus,
        *,
        error_message: str | None = None,
    ) -> DocumentRow:
        row = self.require(document_id)
        row.processing_status = status
        row.error_message = error_message
        return row

    def save_document(self, document_id: str, document: Document) -> DocumentRow:
        """Persists a finished ``Document`` and flips the row to `done`."""
        row = self.require(document_id)
        row.content = _strip_segments(document.model_dump(mode="json"))
        row.total_pages = document.total_pages
        row.ocr_engine = document.ocr_engine
        row.schema_version = document.schema_version
        row.processing_status = ProcessingStatus.DONE
        row.error_message = None
        return row

    def load_document(self, row: DocumentRow) -> Document:
        """Rebuilds the full ``Document`` from the stored (stripped) content."""
        content = _upcast(row.content, row.schema_version)
        return Document.model_validate(_reconstruct_segments(content))


# Pure helpers (no repository state)


def _strip_segments(content: dict) -> dict:
    """Drops per-segment pages/raw_text; pages live once at content['pages']."""
    for segment in content["segments"]:
        segment.pop("pages", None)
        segment.pop("raw_text", None)
    return content


def _reconstruct_segments(content: dict) -> dict:
    """Re-attaches each segment's pages (by page range) and raw_text."""
    pages_by_number = {page["page_number"]: page for page in content["pages"]}
    for segment in content["segments"]:
        pages = [
            pages_by_number[number]
            for number in range(segment["start_page"], segment["end_page"] + 1)
            if number in pages_by_number
        ]
        segment["pages"] = pages
        # Same join convention as make_segment in the segmentation stage.
        segment["raw_text"] = "\n\n\n".join(page["raw_text"] for page in pages)
    return content


def _upcast(content: dict | None, version: int) -> dict:
    """Schema-version hook: identity for v1; future migrations chain here."""
    if content is None:
        raise ValueError("document has no stored content yet")
    if version > CURRENT_SCHEMA_VERSION:
        raise ValueError(
            f"document schema {version} is newer than supported {CURRENT_SCHEMA_VERSION}"
        )
    return content
