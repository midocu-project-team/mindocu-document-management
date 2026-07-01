"""Data access for blocks (single block by its composite key)."""

import uuid

from sqlalchemy.orm import Session

from api.db.models import Block


class BlockRepository:
    """Read access for ``blocks`` by their natural ``(document_id, block_id)`` key."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, document_id: uuid.UUID, block_id: int) -> Block | None:
        return self.session.get(Block, (document_id, block_id))
