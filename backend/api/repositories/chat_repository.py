"""Data access for chat sessions and their messages."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from api.db.models import ChatMessage, ChatMessageReference, ChatSession


class ChatRepository:
    """CRUD + eager-loaded reads for ``chat_sessions``/``chat_messages``."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_session(self, document_id: uuid.UUID) -> ChatSession:
        chat_session = ChatSession(document_id=document_id)
        self.session.add(chat_session)
        self.session.flush()  # populate session_id without committing
        return chat_session

    def list_for_document(self, document_id: uuid.UUID) -> list[ChatSession]:
        """All sessions of a document, oldest first (no messages loaded)."""
        statement = (
            select(ChatSession)
            .where(ChatSession.document_id == document_id)
            .order_by(ChatSession.created_at)
        )
        return list(self.session.scalars(statement))

    def get(self, session_id: uuid.UUID) -> ChatSession | None:
        """A single session with its messages and their grounded references."""
        statement = (
            select(ChatSession)
            .where(ChatSession.session_id == session_id)
            .options(
                selectinload(ChatSession.messages)
                .selectinload(ChatMessage.references)
                .selectinload(ChatMessageReference.reference_blocks)
            )
        )
        return self.session.scalars(statement).first()

    def delete(self, chat_session: ChatSession) -> None:
        self.session.delete(chat_session)  # ORM cascade removes messages/references
