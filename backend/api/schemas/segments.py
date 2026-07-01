"""Request/response models for the granular segment endpoints."""

import uuid

from pydantic import BaseModel

from api.db.models import Segment
from pipeline.datatypes import SummaryReference


class SegmentDetail(BaseModel):
    """A single segment with everything the detail view needs, incl. references."""

    segment_id: uuid.UUID
    document_id: uuid.UUID
    start_page: int
    end_page: int
    confidence: float | None
    title: str | None
    summary: str | None
    relevance: bool
    matched_keywords: list[str]
    references: list[SummaryReference]

    @classmethod
    def from_segment(cls, segment: Segment) -> "SegmentDetail":
        return cls(
            segment_id=segment.segment_id,
            document_id=segment.document_id,
            start_page=segment.start_page,
            end_page=segment.end_page,
            confidence=segment.confidence,
            title=segment.title,
            summary=segment.summary,
            relevance=segment.relevance,
            matched_keywords=list(segment.matched_keywords),
            references=[
                SummaryReference(
                    text=reference.text,
                    block_ids=[link.block_id for link in reference.reference_blocks],
                )
                for reference in segment.references
            ],
        )


class SegmentUpdate(BaseModel):
    """Manual edit of a segment. Only the relevance flag is editable for now."""

    relevance: bool
