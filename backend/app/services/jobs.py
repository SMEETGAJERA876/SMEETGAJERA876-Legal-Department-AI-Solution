"""Processing queue: uploaded documents wait in the database until a worker claims one.

- The queue *is* the `documents` table: status `uploaded` = waiting. Nothing else to run or
  lose — a queued document survives restarts and deployments.
- Workers claim with `SELECT … FOR UPDATE SKIP LOCKED`, so any number of worker threads, API
  processes and machines can share one queue without processing a document twice.
- A worker updates `processing_heartbeat_at` at every step. A document whose heartbeat has
  gone quiet (its worker crashed or the machine restarted) is put back in the queue, up to
  MAX_ATTEMPTS times; unexpected errors are retried the same way.

PROCESSING_MODE=inline (tests, single-process development) processes right after the upload
response instead, as a background task.
"""

import logging
import threading
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import BackgroundTasks
from sqlalchemy import CursorResult, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import Document, DocumentStatus
from app.services.processing import MAX_ATTEMPTS, RETRY_DETAIL, process_document

logger = logging.getLogger("clauselens.jobs")

IDLE_WAIT_SECONDS = 5.0
STALE_AFTER = timedelta(minutes=10)


def requeue_stale(db: Session, now: datetime | None = None) -> int:
    """Documents whose worker went silent go back in the queue (or fail after MAX_ATTEMPTS)."""
    cutoff = (now or datetime.now(UTC)) - STALE_AFTER
    stale = (Document.status == DocumentStatus.PROCESSING) & (
        (Document.processing_heartbeat_at < cutoff) | Document.processing_heartbeat_at.is_(None)
    )
    result: CursorResult[Any] = db.execute(  # type: ignore[assignment]
        update(Document)
        .where(stale & (Document.processing_attempts < MAX_ATTEMPTS))
        .values(status=DocumentStatus.UPLOADED, status_detail=RETRY_DETAIL)
    )
    retried = result.rowcount
    db.execute(
        update(Document)
        .where(stale & (Document.processing_attempts >= MAX_ATTEMPTS))
        .values(
            status=DocumentStatus.FAILED,
            status_detail="Processing failed",
            error_message="Processing was interrupted several times. Please upload it again.",
        )
    )
    db.commit()
    return int(retried or 0)


def claim_next(db: Session) -> uuid.UUID | None:
    """Take the oldest waiting document, safely even with many workers."""
    document = db.scalars(
        select(Document)
        .where(Document.status == DocumentStatus.UPLOADED)
        .order_by(Document.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    ).first()
    if document is None:
        db.rollback()
        return None
    document.status = DocumentStatus.PROCESSING
    document.status_detail = "Starting"
    document.processing_heartbeat_at = datetime.now(UTC)
    document.processing_attempts = (document.processing_attempts or 0) + 1
    db.commit()
    return document.id


def work_once() -> bool:
    """Process one waiting document. False when the queue is empty."""
    with SessionLocal() as db:
        requeue_stale(db)
        document_id = claim_next(db)
    if document_id is None:
        return False
    process_document(document_id)
    return True


class ProcessingQueue:
    """Worker threads that drain the queue; `notify()` wakes them after an upload."""

    def __init__(self) -> None:
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

    def start(self, workers: int) -> None:
        for index in range(workers):
            thread = threading.Thread(
                target=self._run, name=f"clauselens-worker-{index}", daemon=True
            )
            thread.start()
            self._threads.append(thread)

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()

    def notify(self) -> None:
        self._wake.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                busy = work_once()
            except Exception:
                logger.exception("Processing worker error")
                busy = False
            if not busy:
                self._wake.wait(IDLE_WAIT_SECONDS)
                self._wake.clear()


queue = ProcessingQueue()


def enqueue(background_tasks: BackgroundTasks, document_id: uuid.UUID) -> None:
    """Start processing a newly stored document (status `uploaded`)."""
    if get_settings().processing_mode == "inline":
        background_tasks.add_task(process_document, document_id)
    else:
        queue.notify()
