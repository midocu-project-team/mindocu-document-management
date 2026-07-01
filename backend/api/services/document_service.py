"""Document-level orchestration: upload + validation, status, reads.

Upload validates the PDF count and bytes, stores the file, inserts a `pending`
row and enqueues a background job. The heavy pipeline work happens in the job
(see ``pipeline_jobs``), not here.
"""

import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from api import storage
from api.db.models import Case, DocumentRow
from api.exceptions import CaseNotFoundError, InvalidUploadError, TooManyDocumentsError
from api.repositories import CaseRepository, DocumentRepository
from api.services.pipeline_jobs import JobQueue, PipelineJob
from api.settings import Settings
from pipeline import Document

_PDF_MAGIC = b"%PDF-"


class DocumentService:
    """Upload + read paths for documents within a case."""

    def __init__(self, session: Session, job_queue: JobQueue, settings: Settings) -> None:
        self.session = session
        self.job_queue = job_queue
        self.settings = settings
        self.documents = DocumentRepository(session)
        self.cases = CaseRepository(session)

    def upload_documents(
        self, case_id: uuid.UUID, uploads: list[UploadFile]
    ) -> list[DocumentRow]:
        """Stores 1..N PDFs as `pending` rows and enqueues a job per document."""
        self._require_case(case_id)
        self._check_count(case_id, len(uploads))
        rows = [self._store_one(case_id, upload) for upload in uploads]
        self.session.commit()  # rows are durable before any job touches them
        for row in rows:
            self.job_queue.submit(
                PipelineJob(
                    document_id=row.document_id,
                    pdf_path=row.pdf_path,
                    file_name=row.file_name,
                )
            )
        return rows

    def get_case_status(self, case_id: uuid.UUID) -> Case:
        """Returns the case (with its documents) for status polling."""
        return self._require_case(case_id)

    def get_document_full(self, document_id: uuid.UUID) -> Document:
        """Rebuilds the full ``Document`` (pages + blocks) for the detail view."""
        return self.documents.load_document(document_id)

    def get_pdf(self, document_id: uuid.UUID) -> tuple[DocumentRow, Path]:
        """The document row plus its on-disk PDF path."""
        row = self.documents.require(document_id)
        return row, Path(row.pdf_path)

    # Internal helpers

    def _store_one(self, case_id: uuid.UUID, upload: UploadFile) -> DocumentRow:
        data = upload.file.read()
        _validate_pdf(upload.filename, data)
        document_id = uuid.uuid4()
        path = storage.save_pdf(case_id, document_id, data, self.settings.storage_dir)
        return self.documents.create_pending(
            document_id=document_id,
            case_id=case_id,
            file_name=upload.filename or f"{document_id}.pdf",
            file_size_bytes=len(data),
            pdf_path=str(path),
        )

    def _check_count(self, case_id: uuid.UUID, incoming: int) -> None:
        if incoming == 0:
            raise InvalidUploadError(None)
        existing = self.documents.count_for_case(case_id)
        if existing + incoming > self.settings.max_pdfs_per_case:
            raise TooManyDocumentsError(self.settings.max_pdfs_per_case)

    def _require_case(self, case_id: uuid.UUID) -> Case:
        case = self.cases.get(case_id)
        if case is None:
            raise CaseNotFoundError(case_id)
        return case


# Pure helpers (no service state)


def _validate_pdf(file_name: str | None, data: bytes) -> None:
    """Rejects non-PDF uploads by magic bytes (not just the extension)."""
    if data[:5] != _PDF_MAGIC:
        raise InvalidUploadError(file_name)
