"""Chat endpoints: sessions scoped to a document, and posting a question.

Routes span two prefixes (document-scoped session list/create, then
session-scoped detail/messages/delete), so the router carries no single
prefix -- each route spells out its full path instead.
"""

import uuid

from fastapi import APIRouter, status

from api.dependencies import ChatServiceDep
from api.schemas.chat import (
    ChatMessageCreate,
    ChatMessageOut,
    ChatSessionDetail,
    ChatSessionSummary,
)

router = APIRouter(tags=["chat"])


@router.get("/documents/{document_id}/chat/sessions", response_model=list[ChatSessionSummary])
def list_chat_sessions(
    document_id: uuid.UUID, service: ChatServiceDep
) -> list[ChatSessionSummary]:
    """A document's chat sessions, oldest first (sidebar "Chat Sessions" tab)."""
    return [
        ChatSessionSummary.from_session(session)
        for session in service.list_sessions(document_id)
    ]


@router.post(
    "/documents/{document_id}/chat/sessions",
    response_model=ChatSessionSummary,
    status_code=status.HTTP_201_CREATED,
)
def create_chat_session(document_id: uuid.UUID, service: ChatServiceDep) -> ChatSessionSummary:
    """Starts a new, empty chat session for a document ("neue Unterhaltung")."""
    return ChatSessionSummary.from_session(service.create_session(document_id))


@router.get("/chat/sessions/{session_id}", response_model=ChatSessionDetail)
def get_chat_session(session_id: uuid.UUID, service: ChatServiceDep) -> ChatSessionDetail:
    """A session with every message and its grounded references."""
    return ChatSessionDetail.from_session(service.get_session(session_id))


@router.post("/chat/sessions/{session_id}/messages", response_model=ChatMessageOut)
def post_chat_message(
    session_id: uuid.UUID, payload: ChatMessageCreate, service: ChatServiceDep
) -> ChatMessageOut:
    """Asks a question in a session; returns the grounded assistant reply.

    Synchronous: the request blocks until the local model has answered (no
    streaming, no background job queue -- can be slow on a local model).
    """
    return ChatMessageOut.from_message(
        service.post_message(session_id, payload.question)
    )


@router.delete("/chat/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_session(session_id: uuid.UUID, service: ChatServiceDep) -> None:
    service.delete_session(session_id)
