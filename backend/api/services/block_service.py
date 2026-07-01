"""Block-level orchestration: fetch a single block by document + block id."""

import uuid

from sqlalchemy.orm import Session

from api.db.models import Block
from api.exceptions import BlockNotFoundError
from api.repositories import BlockRepository


class BlockService:
    """Read path for a single content block."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.blocks = BlockRepository(session)

    def get_block(self, document_id: uuid.UUID, block_id: int) -> Block:
        block = self.blocks.get(document_id, block_id)
        if block is None:
            raise BlockNotFoundError(document_id, block_id)
        return block
