"""Document processing pipeline: pages → chunks → clauses → embeddings → facts."""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import (
    Clause,
    Document,
    DocumentChunk,
    DocumentPage,
    DocumentStatus,
    LegalFact,
)
from app.services import embeddings, extraction, storage
from app.services.chunking import chunk_pages
from app.services.classification import classify
from app.services.parsing import DocumentParseError, parse_file

logger = logging.getLogger("clauselens.processing")

PARTY_DETECTION_PAGES = 2


def _set_status(db: Session, document: Document, status: DocumentStatus, detail: str) -> None:
    document.status = status
    document.status_detail = detail
    db.commit()


def _clear_derived_data(db: Session, document_id: uuid.UUID) -> None:
    for model in (LegalFact, Clause, DocumentChunk, DocumentPage):
        db.execute(delete(model).where(model.document_id == document_id))


def process_document(document_id: uuid.UUID) -> None:
    """Run the full pipeline. Intended to run as a background task with its own session."""
    with SessionLocal() as db:
        document = db.get(Document, document_id)
        if document is None:
            return
        try:
            _run_pipeline(db, document)
        except DocumentParseError as error:
            db.rollback()
            document.error_message = str(error)
            _set_status(db, document, DocumentStatus.FAILED, "Could not read the document")
        except Exception:
            logger.exception("Processing failed for document %s", document_id)
            db.rollback()
            document.error_message = (
                "Something unexpected happened while processing this document. "
                "Try uploading it again. If it keeps failing, the PDF may use an unusual format."
            )
            _set_status(db, document, DocumentStatus.FAILED, "Processing failed")


def _run_pipeline(db: Session, document: Document) -> None:
    document.error_message = None
    _set_status(db, document, DocumentStatus.PROCESSING, "Reading pages")
    try:
        data = storage.read_file(document.stored_filename)
    except FileNotFoundError as error:
        raise DocumentParseError("The uploaded file is missing. Please upload it again.") from error
    pages = parse_file(data, document.format).page_texts

    _clear_derived_data(db, document.id)
    document.page_count = len(pages)
    db.add_all(
        DocumentPage(document_id=document.id, page_number=i, text=text)
        for i, text in enumerate(pages, start=1)
    )
    _set_status(db, document, DocumentStatus.PROCESSING, f"Finding clauses in {len(pages)} pages")

    chunks, clauses = chunk_pages(pages)
    db.add_all(
        Clause(
            document_id=document.id,
            page_number=c.page_number,
            clause_ref=c.clause_ref,
            heading=c.heading,
            text=c.text,
        )
        for c in clauses
    )
    _set_status(db, document, DocumentStatus.PROCESSING, "Understanding the meaning of each part")

    vectors = embeddings.embed_passages(
        [f"{c.heading}: {c.text}" if c.heading else c.text for c in chunks]
    )
    chunk_rows = [
        DocumentChunk(
            document_id=document.id,
            page_number=c.page_number,
            chunk_index=c.chunk_index,
            clause_ref=c.clause_ref,
            heading=c.heading,
            text=c.text,
            embedding=vector,
        )
        for c, vector in zip(chunks, vectors, strict=True)
    ]
    db.add_all(chunk_rows)
    db.flush()
    _set_status(db, document, DocumentStatus.PROCESSING, "Extracting important information")

    facts = extraction.extract_facts([(c.chunk_index, c.text, c.heading) for c in chunks])
    db.add_all(
        LegalFact(
            document_id=document.id,
            chunk_id=chunk_rows[f.chunk_index].id,
            concept=f.concept,
            value=f.value,
            page_number=chunk_rows[f.chunk_index].page_number,
            clause_ref=chunk_rows[f.chunk_index].clause_ref,
            source_text=f.source_text,
            confidence=f.confidence,
            normalized_value=f.normalized_value,
        )
        for f in facts
    )
    classification = classify(pages, [c.heading for c in clauses if c.heading])
    document.document_type = classification.display_name
    document.document_type_id = classification.document_type
    document.category = classification.category
    document.classification = classification.to_json()
    document.parties = extraction.detect_parties(" ".join(pages[:PARTY_DETECTION_PAGES]))
    document.processed_at = datetime.now(UTC)
    _set_status(db, document, DocumentStatus.READY, "Ready")
