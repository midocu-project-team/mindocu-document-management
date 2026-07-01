"""Response models for document/case processing status (polling)."""

import uuid

from pydantic import BaseModel

from api.db.models import Case, DocumentRow, ProcessingStatus
from api.schemas.cases import case_status_label


class DocumentStatus(BaseModel):
    """Per-document processing status (current stage = processing_status)."""

    document_id: uuid.UUID
    file_name: str
    processing_status: ProcessingStatus
    error_message: str | None

    @classmethod
    def from_row(cls, row: DocumentRow) -> "DocumentStatus":
        return cls(
            document_id=row.document_id,
            file_name=row.file_name,
            processing_status=row.processing_status,
            error_message=row.error_message,
        )


class CaseStatus(BaseModel):
    """Polling payload: aggregated case status + per-document status."""

    case_id: uuid.UUID
    status: str
    documents: list[DocumentStatus]

    @classmethod
    def from_case(cls, case: Case) -> "CaseStatus":
        return cls(
            case_id=case.id,
            status=case_status_label(case.documents),
            documents=[DocumentStatus.from_row(d) for d in case.documents],
        )
