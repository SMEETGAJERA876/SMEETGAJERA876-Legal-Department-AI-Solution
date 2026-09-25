import uuid
from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base_columns import CreatedAtMixin, IdMixin


class Conversation(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "conversations"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    messages: Mapped[list["Message"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="Message.created_at"
    )


class Message(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    citations: Mapped[list["Citation"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )


class Citation(IdMixin, Base):
    __tablename__ = "citations"

    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), index=True
    )
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="SET NULL")
    )
    page_number: Mapped[int] = mapped_column(Integer)
    clause_ref: Mapped[str | None] = mapped_column(String(50))
    quote: Mapped[str] = mapped_column(Text)
