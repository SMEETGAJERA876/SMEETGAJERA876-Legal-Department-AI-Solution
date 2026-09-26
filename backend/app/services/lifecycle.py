"""Document lifecycle jobs: resume processing after a restart, retention, and erasing a user's
data. Run at startup and periodically by app.main's lifespan."""

import logging
import threading
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import Document, DocumentStatus
from app.services import audit, storage
from app.services.processing import process_document

logger = logging.getLogger("clauselens.lifecycle")

UNFINISHED = (DocumentStatus.UPLOADED, DocumentStatus.PROCESSING)


def unfinished_document_ids(db: Session) -> list[uuid.UUID]:
    return list(db.scalars(select(Document.id).where(Document.status.in_(UNFINISHED))))


def resume_unfinished() -> int:
    """Documents whose processing was interrupted (e.g. by a restart) are processed again."""
    with SessionLocal() as db:
        ids = unfinished_document_ids(db)
    for document_id in ids:
        logger.info("Resuming interrupted processing of document %s", document_id)
        process_document(document_id)
    return len(ids)


def delete_documents(db: Session, documents: list[Document], action: str) -> int:
    """Delete documents with all derived data (cascade) and their files; audit each one."""
    files = []
    for document in documents:
        files.append(document.stored_filename)
        audit.record(db, action, user_id=document.user_id, document_id=document.id)
        db.delete(document)
    db.commit()
    for stored_filename in files:
        storage.delete_file(stored_filename)
    return len(files)


def apply_retention(now: datetime | None = None) -> int:
    """Delete documents older than RETENTION_DAYS (0 = keep until the user deletes them)."""
    days = get_settings().retention_days
    if days <= 0:
        return 0
    cutoff = (now or datetime.now(UTC)) - timedelta(days=days)
    with SessionLocal() as db:
        # Demo documents are part of the deployment, not somebody's upload: retention skips them.
        expired = list(
            db.scalars(
                select(Document).where(
                    Document.created_at < cutoff, Document.is_demo.is_(False)
                )
            )
        )
        deleted = delete_documents(db, expired, audit.RETENTION_DELETE)
    if deleted:
        logger.info("Retention: deleted %d document(s) older than %d days", deleted, days)
    return deleted


class PeriodicJobs:
    """Retention runs in a daemon thread every RETENTION_CHECK_HOURS."""

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="clauselens-jobs", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        # In queue mode the workers pick up waiting documents and requeue interrupted ones
        # themselves (services/jobs.py); inline mode has no workers, so resume here.
        if get_settings().processing_mode == "inline":
            try:
                resume_unfinished()
            except Exception:
                logger.exception("Resuming unfinished documents failed")
        interval = get_settings().retention_check_hours * 3600
        while not self._stop.is_set():
            try:
                apply_retention()
            except Exception:
                logger.exception("Retention job failed")
            self._stop.wait(interval)
