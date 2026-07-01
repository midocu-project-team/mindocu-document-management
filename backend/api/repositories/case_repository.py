"""Data access for cases (and their document rows by relationship)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from api.db.models import Case, DocumentRow


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

    def get_with_segments(self, case_id: uuid.UUID) -> Case | None:
        """A case with its documents and each document's segments eagerly loaded.

        Segments only -- not pages/blocks -- so the detail view stays slim.
        """
        statement = (
            select(Case)
            .where(Case.id == case_id)
            .options(selectinload(Case.documents).selectinload(DocumentRow.segments))
        )
        return self.session.scalars(statement).first()

    def rename(self, case: Case, name: str) -> None:
        case.name = name

    def delete(self, case: Case) -> None:
        self.session.delete(case)  # ORM cascade removes the document rows
