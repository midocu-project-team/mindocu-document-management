"""Data access for segments (list per document, single with its references)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from api.db.models import Segment, SummaryReference


class SegmentRepository:
    """Read + relevance-toggle access for ``segments``."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_document(self, document_id: uuid.UUID) -> list[Segment]:
        """All segments of a document, in reading order (no references loaded)."""
        statement = (
            select(Segment)
            .where(Segment.document_id == document_id)
            .order_by(Segment.start_page)
        )
        return list(self.session.scalars(statement))

    def get(self, segment_id: uuid.UUID) -> Segment | None:
        """A single segment with its references and their grounded blocks."""
        statement = (
            select(Segment)
            .where(Segment.segment_id == segment_id)
            .options(
                selectinload(Segment.references).selectinload(
                    SummaryReference.reference_blocks
                )
            )
        )
        return self.session.scalars(statement).first()
