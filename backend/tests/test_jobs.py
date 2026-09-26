"""The processing queue (services/jobs.py): claiming, concurrency, retries and crash recovery."""

import threading
import time
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Document, DocumentStatus
from app.services import jobs, processing, storage


def queued_document(pdf: bytes, name: str = "queued.pdf") -> uuid.UUID:
    """A stored upload waiting in the queue (status `uploaded`), as the upload route leaves it."""
    stored = storage.new_stored_filename()
    storage.write_file(stored, pdf)
    with SessionLocal() as db:
        document = Document(
            original_filename=name,
            stored_filename=stored,
            file_size=len(pdf),
            status=DocumentStatus.UPLOADED,
            status_detail="Waiting to be processed",
        )
        db.add(document)
        db.commit()
        return document.id


def load(document_id: uuid.UUID) -> Document:
    with SessionLocal() as db:
        document = db.get(Document, document_id)
        assert document is not None
        db.expunge(document)
        return document


def drain_queue() -> None:
    while jobs.work_once():
        pass


@pytest.fixture(autouse=True)
def empty_queue(database: None) -> None:
    drain_queue()  # leftovers from other tests must not interfere


def test_worker_processes_a_queued_upload(sample_pdf: bytes) -> None:
    document_id = queued_document(sample_pdf)
    assert jobs.work_once()
    document = load(document_id)
    assert document.status == DocumentStatus.READY
    assert document.processing_attempts == 1
    assert document.processing_heartbeat_at is not None
    assert not jobs.work_once()  # queue is empty now


def test_two_workers_never_claim_the_same_document(sample_pdf: bytes) -> None:
    ids = {queued_document(sample_pdf, f"c{i}.pdf") for i in range(2)}
    claimed: list[uuid.UUID | None] = []
    barrier = threading.Barrier(2)

    def claim() -> None:
        with SessionLocal() as db:
            barrier.wait()
            claimed.append(jobs.claim_next(db))

    threads = [threading.Thread(target=claim) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert set(claimed) == ids  # each document claimed exactly once
    for document_id in ids:  # finish them so the queue is clean
        processing.process_document(document_id)


def test_worker_pool_drains_the_queue(sample_pdf: bytes) -> None:
    ids = [queued_document(sample_pdf, f"pool{i}.pdf") for i in range(3)]
    pool = jobs.ProcessingQueue()
    pool.start(workers=2)
    pool.notify()
    try:
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            if all(load(i).status == DocumentStatus.READY for i in ids):
                break
            time.sleep(0.5)
    finally:
        pool.stop()
    documents = [load(i) for i in ids]
    assert all(d.status == DocumentStatus.READY for d in documents)
    assert all(d.processing_attempts == 1 for d in documents)  # none processed twice


def test_unexpected_error_is_retried_then_fails(
    sample_pdf: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*_: object, **__: object) -> None:
        raise RuntimeError("simulated crash in the pipeline")

    monkeypatch.setattr(processing, "chunk_pages", broken)
    document_id = queued_document(sample_pdf, "flaky.pdf")
    for attempt in range(1, processing.MAX_ATTEMPTS + 1):
        assert jobs.work_once()
        document = load(document_id)
        assert document.processing_attempts == attempt
        expected = (
            DocumentStatus.FAILED if attempt == processing.MAX_ATTEMPTS else DocumentStatus.UPLOADED
        )
        assert document.status == expected
    assert load(document_id).error_message


def test_interrupted_processing_is_requeued_or_failed(sample_pdf: bytes) -> None:
    fresh, stale, exhausted = (queued_document(sample_pdf, f"s{i}.pdf") for i in range(3))
    long_ago = datetime.now(UTC) - jobs.STALE_AFTER - timedelta(minutes=1)
    with SessionLocal() as db:
        for document_id, heartbeat, attempts in (
            (fresh, datetime.now(UTC), 1),
            (stale, long_ago, 1),
            (exhausted, long_ago, processing.MAX_ATTEMPTS),
        ):
            document = db.get(Document, document_id)
            assert document is not None
            document.status = DocumentStatus.PROCESSING
            document.processing_heartbeat_at = heartbeat
            document.processing_attempts = attempts
        db.commit()
        assert jobs.requeue_stale(db) == 1
    assert load(fresh).status == DocumentStatus.PROCESSING  # its worker is still alive
    assert load(stale).status == DocumentStatus.UPLOADED
    assert load(exhausted).status == DocumentStatus.FAILED
    with SessionLocal() as db:  # clean up
        for document in db.scalars(select(Document).where(Document.id.in_([fresh, stale]))):
            db.delete(document)
        db.commit()
    drain_queue()
