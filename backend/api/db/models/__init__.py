"""ORM models package: one module per entity, re-exported here.

Importing this package registers every mapping on ``Base.metadata`` so
``create_all`` (tests) and Alembic autogenerate see all tables. Import order is
irrelevant because relationships and foreign keys are declared by string name.
Existing call sites keep working via ``from api.db.models import ...``.
"""

from api.db.models.block import Block
from api.db.models.case import Case
from api.db.models.chat import (
    ChatMessage,
    ChatMessageReference,
    ChatReferenceBlock,
    ChatSession,
)
from api.db.models.document import DocumentRow, ProcessingStatus
from api.db.models.page import Page
from api.db.models.reference import ReferenceBlock, SummaryReference
from api.db.models.segment import Segment

__all__ = [
    "Case",
    "DocumentRow",
    "ProcessingStatus",
    "Page",
    "Block",
    "Segment",
    "SummaryReference",
    "ReferenceBlock",
    "ChatSession",
    "ChatMessage",
    "ChatMessageReference",
    "ChatReferenceBlock",
]
