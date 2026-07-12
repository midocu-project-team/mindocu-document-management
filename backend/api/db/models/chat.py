"""ORM models for document chat: sessions, messages and their grounding.

Mirrors the segment/summary_reference/reference_block shape 1:1: a
``ChatMessage`` is one turn (user question or assistant answer); an
assistant message's answer is split into ordered ``ChatMessageReference``
rows (one per grounded sentence, ``seq``-ordered) exactly like a segment's
``SummaryReference``, each grounded in the blocks it cites via
``ChatReferenceBlock`` (the same M:N junction shape as ``ReferenceBlock``).
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db.base import Base


class ChatSession(Base):
    """One chat conversation scoped to a single document."""

    __tablename__ = "chat_sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        index=True,
    )
    # Auto-filled from the first user question (truncated); None until then.
    title: Mapped[str | None] = mapped_column(String, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    document: Mapped["DocumentRow"] = relationship(back_populates="chat_sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ChatMessage.seq",
    )


class ChatMessage(Base):
    """One turn of a chat session: a user question or a grounded assistant answer."""

    __tablename__ = "chat_messages"
    __table_args__ = (
        UniqueConstraint("session_id", "seq", name="uq_chat_messages_session_seq"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.session_id", ondelete="CASCADE"),
        index=True,
    )
    seq: Mapped[int] = mapped_column(Integer)  # 0-based order within the session
    role: Mapped[str] = mapped_column(String(20))  # "user" | "assistant"
    # Denormalized write-once cache (join of references' text), same idea as
    # Segment.summary; the source of truth is `references` for assistant
    # messages, this column directly for user messages.
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session: Mapped["ChatSession"] = relationship(back_populates="messages")
    references: Mapped[list["ChatMessageReference"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ChatMessageReference.seq",
    )


class ChatMessageReference(Base):
    """One ordered, grounded sentence of an assistant message. Mirrors SummaryReference."""

    __tablename__ = "chat_message_references"
    __table_args__ = (
        UniqueConstraint(
            "message_id", "seq", name="uq_chat_message_references_message_seq"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    message_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        index=True,
    )
    seq: Mapped[int] = mapped_column(Integer)  # 0-based order within the message
    text: Mapped[str] = mapped_column(Text)

    message: Mapped["ChatMessage"] = relationship(back_populates="references")
    reference_blocks: Mapped[list["ChatReferenceBlock"]] = relationship(
        back_populates="reference",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ChatReferenceBlock.block_id",
    )


class ChatReferenceBlock(Base):
    """Junction: a chat reference grounded in a block. Mirrors ReferenceBlock."""

    __tablename__ = "chat_reference_blocks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["document_id", "block_id"],
            ["blocks.document_id", "blocks.block_id"],
            ondelete="CASCADE",
        ),
    )

    reference_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_message_references.id", ondelete="CASCADE"),
        primary_key=True,
    )
    block_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))

    reference: Mapped["ChatMessageReference"] = relationship(
        back_populates="reference_blocks"
    )
