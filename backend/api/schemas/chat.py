"""Request/response models for document chat sessions and messages."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from pipeline.datatypes import SummaryReference

from api.db.models import ChatMessage, ChatSession


class ChatSessionSummary(BaseModel):
    """One chat session without its messages (drives the sessions list)."""

    session_id: uuid.UUID
    document_id: uuid.UUID
    title: str | None
    created_at: datetime

    @classmethod
    def from_session(cls, chat_session: ChatSession) -> "ChatSessionSummary":
        return cls(
            session_id=chat_session.session_id,
            document_id=chat_session.document_id,
            title=chat_session.title,
            created_at=chat_session.created_at,
        )


class ChatMessageOut(BaseModel):
    """One turn of a chat session; `references` is empty for user messages."""

    message_id: int
    role: Literal["user", "assistant"]
    text: str
    references: list[SummaryReference]
    created_at: datetime

    @classmethod
    def from_message(cls, message: ChatMessage) -> "ChatMessageOut":
        return cls(
            message_id=message.id,
            role=message.role,
            text=message.text,
            references=[
                SummaryReference(
                    text=reference.text,
                    block_ids=[link.block_id for link in reference.reference_blocks],
                )
                for reference in message.references
            ],
            created_at=message.created_at,
        )


class ChatSessionDetail(BaseModel):
    """Full session detail incl. every message (GET /chat/sessions/{id})."""

    session_id: uuid.UUID
    document_id: uuid.UUID
    title: str | None
    created_at: datetime
    messages: list[ChatMessageOut]

    @classmethod
    def from_session(cls, chat_session: ChatSession) -> "ChatSessionDetail":
        return cls(
            session_id=chat_session.session_id,
            document_id=chat_session.document_id,
            title=chat_session.title,
            created_at=chat_session.created_at,
            messages=[ChatMessageOut.from_message(m) for m in chat_session.messages],
        )


class ChatMessageCreate(BaseModel):
    """A new user question posted to a session."""

    question: str = Field(min_length=1)
