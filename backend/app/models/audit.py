import uuid
from typing import Any

from sqlalchemy import ForeignKey, Index, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base_columns import CreatedAtMixin, IdMixin


class AuditEvent(IdMixin, CreatedAtMixin, Base):
    """Who did what to which document, and when (app/services/audit.py).

    document_id is deliberately not a foreign key: the record of a deletion must outlive the
    document. Events are deleted with the user's account ("delete all my data").
    """

    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_events_user_created", "user_id", "created_at"),)

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    action: Mapped[str] = mapped_column(String(40))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
