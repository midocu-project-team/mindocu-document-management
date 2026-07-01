"""Request/response models for cases (slim; never the pipeline models)."""

import uuid
from collections.abc import Iterable
from datetime import datetime

from pydantic import BaseModel, Field

from api.db.models import Case, DocumentRow, ProcessingStatus, Segment

# Statuses that mean a document is still being processed.
_IN_FLIGHT = {
    ProcessingStatus.PENDING,
    ProcessingStatus.EXTRACTING,
    ProcessingStatus.SEGMENTING,
    ProcessingStatus.ENRICHING,
}


def case_status_label(documents: Iterable[DocumentRow]) -> str:
    """Aggregated case status for the homepage: 'processing' vs 'done'."""
    return "processing" if any(d.processing_status in _IN_FLIGHT for d in documents) else "done"


class CaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class CaseRename(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class SegmentSummary(BaseModel):
    """One enriched segment without pages/blocks (drives the segment list/filter)."""

    segment_id: uuid.UUID
    title: str | None
    summary: str | None
    relevance: bool
    matched_keywords: list[str]
    start_page: int
    end_page: int

    @classmethod
    def from_segment(cls, segment: Segment) -> "SegmentSummary":
        return cls(
            segment_id=segment.segment_id,
            title=segment.title,
            summary=segment.summary,
            relevance=segment.relevance,
            matched_keywords=list(segment.matched_keywords),
            start_page=segment.start_page,
            end_page=segment.end_page,
        )


class DocumentSummary(BaseModel):
    """A document with its segment count -- segments are fetched separately.

    The full segment list lives behind ``GET /documents/{id}/segments`` so the
    case detail stays slim; only the count is kept here (for the doc dropdown).
    """

    document_id: uuid.UUID
    file_name: str
    processing_status: ProcessingStatus
    total_pages: int
    segment_count: int

    @classmethod
    def from_row(cls, row: DocumentRow, segment_count: int) -> "DocumentSummary":
        return cls(
            document_id=row.document_id,
            file_name=row.file_name,
            processing_status=row.processing_status,
            total_pages=row.total_pages,
            segment_count=segment_count,
        )


class CaseSummary(BaseModel):
    """List/homepage view of a case."""

    id: uuid.UUID
    name: str
    created_at: datetime
    status: str
    document_count: int

    @classmethod
    def from_case(cls, case: Case) -> "CaseSummary":
        return cls(
            id=case.id,
            name=case.name,
            created_at=case.created_at,
            status=case_status_label(case.documents),
            document_count=len(case.documents),
        )


class CaseDetail(BaseModel):
    """Case detail: the document list with per-document segment counts."""

    id: uuid.UUID
    name: str
    created_at: datetime
    status: str
    documents: list[DocumentSummary]

    @classmethod
    def from_case(cls, case: Case, segment_counts: dict[uuid.UUID, int]) -> "CaseDetail":
        return cls(
            id=case.id,
            name=case.name,
            created_at=case.created_at,
            status=case_status_label(case.documents),
            documents=[
                DocumentSummary.from_row(d, segment_counts.get(d.document_id, 0))
                for d in case.documents
            ],
        )
