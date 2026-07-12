"""Chat orchestration: sessions, and turning one question into a grounded answer.

Reuses `DocumentRepository.load_document` (the same call the full-document
endpoint uses) to get the pipeline `Document` a `ChatStrategy` needs -- no
separate document-reading path for chat.
"""

import uuid

from sqlalchemy.orm import Session

from pipeline import ChatStrategy
from pipeline.datatypes import ChatTurn, SummaryReference

from api.db.models import ChatMessage, ChatMessageReference, ChatReferenceBlock, ChatSession
from api.exceptions import ChatSessionNotFoundError
from api.repositories import ChatRepository, DocumentRepository

# Session title is the first question, truncated for the sessions-list UI.
TITLE_MAX_CHARS = 80


class ChatService:
    """Orchestrates chat sessions/messages over a document's processed output."""

    def __init__(self, session: Session, chat_strategy: ChatStrategy) -> None:
        self.session = session
        self.chat_strategy = chat_strategy
        self.chats = ChatRepository(session)
        self.documents = DocumentRepository(session)

    def list_sessions(self, document_id: uuid.UUID) -> list[ChatSession]:
        self.documents.require(document_id)
        return self.chats.list_for_document(document_id)

    def create_session(self, document_id: uuid.UUID) -> ChatSession:
        self.documents.require(document_id)
        chat_session = self.chats.create_session(document_id)
        self.session.commit()
        return chat_session

    def get_session(self, session_id: uuid.UUID) -> ChatSession:
        chat_session = self.chats.get(session_id)
        if chat_session is None:
            raise ChatSessionNotFoundError(session_id)
        return chat_session

    def delete_session(self, session_id: uuid.UUID) -> None:
        chat_session = self.get_session(session_id)
        self.chats.delete(chat_session)
        self.session.commit()

    def post_message(self, session_id: uuid.UUID, question: str) -> ChatMessage:
        """Answers `question` in `session_id`, persisting both turns."""
        chat_session = self.get_session(session_id)
        document = self.documents.load_document(chat_session.document_id)
        history = [ChatTurn(role=m.role, text=m.text) for m in chat_session.messages]

        self._append_message(chat_session, role="user", text=question)
        references = self.chat_strategy.answer(document, question, history)
        assistant_message = self._append_message(
            chat_session, role="assistant", text=" ".join(r.text for r in references)
        )
        _attach_references(assistant_message, references, chat_session.document_id)

        if chat_session.title is None:
            chat_session.title = question[:TITLE_MAX_CHARS]

        self.session.commit()
        return assistant_message

    def _append_message(
        self, chat_session: ChatSession, *, role: str, text: str
    ) -> ChatMessage:
        message = ChatMessage(seq=len(chat_session.messages), role=role, text=text)
        chat_session.messages.append(message)
        return message


# Pure helper (no service state)


def _attach_references(
    message: ChatMessage, references: list[SummaryReference], document_id: uuid.UUID
) -> None:
    for seq, reference in enumerate(references):
        reference_row = ChatMessageReference(seq=seq, text=reference.text)
        message.references.append(reference_row)
        for block_id in reference.block_ids:
            reference_row.reference_blocks.append(
                ChatReferenceBlock(block_id=block_id, document_id=document_id)
            )
