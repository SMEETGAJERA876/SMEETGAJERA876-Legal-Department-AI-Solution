import enum
import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Computed,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base_columns import CreatedAtMixin, IdMixin

EMBEDDING_DIMENSIONS = 384
SEARCH_VECTOR_SQL = (
    "setweight(to_tsvector('english'::regconfig, coalesce(heading, '')), 'A') || "
    "setweight(to_tsvector('english'::regconfig, text), 'B')"
)


class DocumentStatus(enum.StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Document(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "documents"

    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str] = mapped_column(String(64), unique=True)
    file_size: Mapped[int] = mapped_column(Integer)
    # FILE FORMAT (how the bytes are stored) — detected from content. Not the document type.
    format: Mapped[str] = mapped_column(String(10), default="pdf", server_default="pdf")
    page_count: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(
            DocumentStatus, name="document_status", values_callable=lambda e: [m.value for m in e]
        ),
        default=DocumentStatus.UPLOADED,
        index=True,
    )
    status_detail: Mapped[str | None] = mapped_column(String(200))
    error_message: Mapped[str | None] = mapped_column(Text)
    document_type: Mapped[str | None] = mapped_column(String(100))  # display name
    # Classification (docs/Document_Classification.md): taxonomy ids + the full result.
    document_type_id: Mapped[str | None] = mapped_column(String(80), index=True)
    category: Mapped[str | None] = mapped_column(String(40), index=True)
    classification: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    parties: Mapped[list[str]] = mapped_column(JSONB, default=list)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Processing queue (services/jobs.py): last sign of life of the worker, and attempts so far.
    processing_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # Set on a corrected copy: the document it was made from, and every change applied.
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL")
    )
    changes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, server_default="[]")
    # Part of the public read-only demo (app/core/auth.py, scripts/seed_demo.py): anyone may
    # read it without signing in. Never set on a document a real person uploaded.
    is_demo: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", index=True
    )

    pages: Mapped[list["DocumentPage"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="DocumentPage.page_number",
    )


class DocumentPage(IdMixin, Base):
    __tablename__ = "document_pages"
    __table_args__ = (UniqueConstraint("document_id", "page_number"),)

    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    page_number: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)

    document: Mapped[Document] = relationship(back_populates="pages")


class DocumentChunk(IdMixin, Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        Index("ix_document_chunks_document_page", "document_id", "page_number"),
        Index("ix_document_chunks_search_vector", "search_vector", postgresql_using="gin"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    page_number: Mapped[int] = mapped_column(Integer)
    chunk_index: Mapped[int] = mapped_column(Integer)
    clause_ref: Mapped[str | None] = mapped_column(String(50))
    heading: Mapped[str | None] = mapped_column(String(300))
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
    # Full-text index for keyword search: the heading counts more (weight A) than the body (B).
    search_vector: Mapped[Any] = mapped_column(
        TSVECTOR,
        Computed(SEARCH_VECTOR_SQL, persisted=True),
        deferred=True,
    )


class Clause(IdMixin, Base):
    __tablename__ = "clauses"
    __table_args__ = (Index("ix_clauses_document_page", "document_id", "page_number"),)

    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    page_number: Mapped[int] = mapped_column(Integer)
    clause_ref: Mapped[str] = mapped_column(String(50))
    heading: Mapped[str | None] = mapped_column(String(300))
    text: Mapped[str] = mapped_column(Text)


class LegalFact(IdMixin, Base):
    """A structured piece of information extracted from the document, always with its source."""

    __tablename__ = "legal_facts"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="SET NULL")
    )
    concept: Mapped[str] = mapped_column(String(50), index=True)
    value: Mapped[str] = mapped_column(String(300))
    page_number: Mapped[int] = mapped_column(Integer)
    clause_ref: Mapped[str | None] = mapped_column(String(50))
    source_text: Mapped[str] = mapped_column(Text)
    # Rule confidence (0-1) and machine-readable value (legal_fact.schema.json).
    confidence: Mapped[float | None] = mapped_column(Float)
    normalized_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
