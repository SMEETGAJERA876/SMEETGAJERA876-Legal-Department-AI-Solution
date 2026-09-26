"""Loading the public read-only demo documents (docs/Demo.md).

The documents come from files shipped with the deployment, are owned by a demo user that has no
Firebase uid, and are flagged `is_demo` — which is what lets an anonymous visitor read them
(app/core/auth.py) and what stops anyone changing them.

Two callers: `scripts.seed_demo` (a person running it once) and, when DEMO_AUTO_SEED is on, a
background thread at start-up (app/main.py) — for hosts where there is no shell to run a script,
and where a restart loses the uploads directory but keeps the database.
"""

import logging
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_demo_user
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import Document, DocumentStatus
from app.services import processing, storage

logger = logging.getLogger("clauselens.demo")

# /app/backend/app/services/demo.py -> /app, which is also the repository root in a checkout.
ROOT = Path(__file__).resolve().parents[3]

# The demo documents, in the order the picker shows them. The real Act first: it is the one that
# shows the system doing something a general-purpose chatbot cannot.
DEMO_FILES = [
    ROOT / "dataset" / "indiacode" / "consumer_protection_act_2019.pdf",
    ROOT / "samples" / "employment_agreement.pdf",
    ROOT / "samples" / "rental_agreement_with_mistakes.pdf",
]


def seeded(db: Session) -> list[Document]:
    return list(
        db.scalars(
            select(Document).where(Document.is_demo.is_(True)).order_by(Document.created_at)
        )
    )


def missing_files() -> list[Path]:
    return [path for path in DEMO_FILES if not path.exists()]


def remove() -> int:
    """Delete every demo document and its file."""
    with SessionLocal() as db:
        documents = seeded(db)
        for document in documents:
            storage.delete_file(document.stored_filename)
            db.delete(document)
        db.commit()
        return len(documents)


def _needs_seeding(db: Session, path: Path) -> Document | None:
    """The existing row for this file, when it is unusable and should be replaced.

    A demo document whose stored file has gone (a host without a persistent disk restarted) is
    worse than none at all: the workspace opens and the PDF fails to load. Replace it.
    """
    existing = db.scalar(
        select(Document).where(Document.is_demo.is_(True), Document.original_filename == path.name)
    )
    if existing is None:
        return None
    usable = existing.status is DocumentStatus.READY and storage.file_exists(
        existing.stored_filename
    )
    return None if usable else existing


def seed_one(path: Path) -> tuple[str, bool]:
    """Load one demo document. Returns (message, did_work)."""
    with SessionLocal() as db:
        stale = _needs_seeding(db, path)
        if stale is None and db.scalar(
            select(Document).where(
                Document.is_demo.is_(True), Document.original_filename == path.name
            )
        ):
            return f"{path.name} — already loaded", False
        if stale is not None:
            storage.delete_file(stale.stored_filename)
            db.delete(stale)
            db.commit()

        data = path.read_bytes()
        stored_filename = storage.new_stored_filename("pdf")
        storage.write_file(stored_filename, data)
        document = Document(
            original_filename=path.name,
            stored_filename=stored_filename,
            file_size=len(data),
            user_id=get_demo_user(db).id,
            format="pdf",
            status=DocumentStatus.UPLOADED,
            status_detail="Waiting to be processed",
            is_demo=True,
        )
        db.add(document)
        db.commit()
        document_id: uuid.UUID = document.id

    # Processing opens its own session and takes a minute on the 42-page Act.
    processing.process_document(document_id)

    with SessionLocal() as db:
        done = db.get(Document, document_id)
        if done is None:
            return f"{path.name} — disappeared while processing", True
        if done.status is not DocumentStatus.READY:
            return f"{path.name} — {done.status.value}: {done.error_message or ''}", True
        return f"{path.name} — ready, {done.page_count} pages, {done.document_type}", True


def seed(log: bool = False) -> list[str]:
    """Load whatever is missing. Safe to call again — documents already loaded are left alone."""
    messages = []
    for path in DEMO_FILES:
        if not path.exists():
            messages.append(f"{path.name} — not in this deployment, skipped")
            continue
        try:
            message, _ = seed_one(path)
        except Exception:
            logger.exception("Could not load the demo document %s", path.name)
            message = f"{path.name} — failed, see the server log"
        messages.append(message)
        if log:
            logger.info("Demo document: %s", message)
    return messages


def auto_seed() -> None:
    """Background start-up task (DEMO_AUTO_SEED). Never lets a demo problem break the API."""
    settings = get_settings()
    if not (settings.demo_mode_enabled and settings.demo_auto_seed):
        return
    try:
        seed(log=True)
    except Exception:
        logger.exception("Demo auto-seeding failed; the API is unaffected")
