"""Segment-level orchestration: list per document, detail, relevance toggle."""

import uuid

from sqlalchemy.orm import Session

from api.db.models import Segment
from api.exceptions import SegmentNotFoundError
from api.repositories import DocumentRepository, SegmentRepository


class SegmentService:
    """Read paths for segments plus the manual relevance override."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.segments = SegmentRepository(session)
        self.documents = DocumentRepository(session)

    def list_for_document(self, document_id: uuid.UUID) -> list[Segment]:
        """All segments of a document (404 if the document is unknown)."""
        self.documents.require(document_id)
        return self.segments.list_for_document(document_id)

    def get_segment(self, segment_id: uuid.UUID) -> Segment:
        segment = self.segments.get(segment_id)
        if segment is None:
            raise SegmentNotFoundError(segment_id)
        return segment

    def update_relevance(self, segment_id: uuid.UUID, relevance: bool) -> Segment:
        """Sets the segment's relevance (user-authoritative); no re-enrichment."""
        segment = self.get_segment(segment_id)
        segment.relevance = relevance
        self.session.commit()
        return segment
