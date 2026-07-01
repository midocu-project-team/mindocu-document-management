"""Data access for cases (and their document rows by relationship)."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from api.db.models import Case, Segment


class CaseRepository:
    """CRUD for ``cases``; deletion cascades to documents via the relationship."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, name: str) -> Case:
        case = Case(name=name)
        self.session.add(case)
        self.session.flush()  # populate case.id without committing
        return case

    def list_with_documents(self) -> list[Case]:
        """All cases, newest first, with documents eagerly loaded for status."""
        statement = (
            select(Case)
            .options(selectinload(Case.documents))
            .order_by(Case.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def get(self, case_id: uuid.UUID) -> Case | None:
        return self.session.get(Case, case_id)

    def get_with_segment_counts(
        self, case_id: uuid.UUID
    ) -> tuple[Case, dict[uuid.UUID, int]] | None:
        """A case with its documents plus a per-document segment count.

        Segments themselves are not loaded (fetched separately via
        ``/documents/{id}/segments``); only their count per document is needed
        for the case detail, so a grouped ``COUNT`` avoids pulling the bodies.
        """
        case = self.session.scalars(
            select(Case).where(Case.id == case_id).options(selectinload(Case.documents))
        ).first()
        if case is None:
            return None
        counts = self._segment_counts([d.document_id for d in case.documents])
        return case, counts

    def _segment_counts(self, document_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
        if not document_ids:
            return {}
        rows = self.session.execute(
            select(Segment.document_id, func.count())
            .where(Segment.document_id.in_(document_ids))
            .group_by(Segment.document_id)
        )
        return {document_id: count for document_id, count in rows}

    def rename(self, case: Case, name: str) -> None:
        case.name = name

    def delete(self, case: Case) -> None:
        self.session.delete(case)  # ORM cascade removes the document rows
