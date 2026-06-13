"""Case-level orchestration over the repositories and PDF storage."""

import uuid

from sqlalchemy.orm import Session

from api import storage
from api.db.models import Case
from api.exceptions import CaseNotFoundError
from api.repositories import CaseRepository
from api.settings import Settings


class CaseService:
    """Create/list/rename/delete cases; delete also removes PDF files."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.cases = CaseRepository(session)

    def create_case(self, name: str) -> Case:
        case = self.cases.create(name)
        self.session.commit()
        return case

    def list_cases(self) -> list[Case]:
        return self.cases.list_with_documents()

    def get_case(self, case_id: uuid.UUID) -> Case:
        return self._require(case_id)

    def rename_case(self, case_id: uuid.UUID, name: str) -> Case:
        case = self._require(case_id)
        self.cases.rename(case, name)
        self.session.commit()
        return case

    def delete_case(self, case_id: uuid.UUID) -> None:
        case = self._require(case_id)
        self.cases.delete(case)
        self.session.commit()  # DB rows (cascade) first ...
        storage.delete_case_dir(case_id, self.settings.storage_dir)  # ... then PDFs

    def _require(self, case_id: uuid.UUID) -> Case:
        case = self.cases.get(case_id)
        if case is None:
            raise CaseNotFoundError(case_id)
        return case
