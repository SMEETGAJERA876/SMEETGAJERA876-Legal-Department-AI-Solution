"""The signed-in user's own data: their activity log, and erasing everything they uploaded."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.db.session import get_db
from app.models import AuditEvent, Document
from app.services import audit, lifecycle

router = APIRouter(prefix="/account", tags=["account"])

DbSession = Annotated[Session, Depends(get_db)]
ACTIVITY_LIMIT = 100


class ActivityOut(BaseModel):
    at: str
    action: str
    label: str
    document_id: str | None
    document_name: str | None


class DeletedOut(BaseModel):
    deleted_documents: int


@router.get("/activity", response_model=list[ActivityOut])
def my_activity(user: CurrentUser, db: DbSession) -> list[ActivityOut]:
    """Everything recorded about the signed-in user's documents, newest first."""
    events = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.user_id == user.id)
        .order_by(AuditEvent.created_at.desc())
        .limit(ACTIVITY_LIMIT)
    ).all()
    ids = {e.document_id for e in events if e.document_id}
    names = dict(
        db.execute(select(Document.id, Document.original_filename).where(Document.id.in_(ids)))
        .tuples()
        .all()
    )
    return [
        ActivityOut(
            at=e.created_at.isoformat(),
            action=e.action,
            label=audit.LABELS.get(e.action, e.action),
            document_id=str(e.document_id) if e.document_id else None,
            document_name=names.get(e.document_id) if e.document_id else None,
        )
        for e in events
    ]


@router.delete("/documents", response_model=DeletedOut)
def delete_all_my_documents(user: CurrentUser, db: DbSession, request: Request) -> DeletedOut:
    """Right to erasure: delete every document of the signed-in user, with its files and all
    data extracted from it. The activity log keeps a record that this happened."""
    documents = list(db.scalars(select(Document).where(Document.user_id == user.id)))
    deleted = lifecycle.delete_documents(db, documents, audit.DELETE)
    audit.record(
        db, audit.DELETE_ALL_DATA, user_id=user.id, request=request, detail={"count": deleted}
    )
    db.commit()
    return DeletedOut(deleted_documents=deleted)
