"""Re-run the full processing pipeline for existing documents (e.g. after extraction improves).

Usage (from backend/):  uv run python -m scripts.reprocess

Pages, clauses, chunks and facts are rebuilt from the stored original files. User-verified
document types are kept.
"""

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Document, DocumentStatus
from app.services.processing import process_document


def main() -> None:
    with SessionLocal() as db:
        documents = list(
            db.execute(
                select(Document.id, Document.original_filename, Document.classification).where(
                    Document.status.in_([DocumentStatus.READY, DocumentStatus.FAILED])
                )
            )
        )
    for document_id, name, classification in documents:
        verified = (classification or {}).get("status") == "user_verified"
        process_document(document_id)
        if verified:
            _restore_classification(document_id, classification)
        print(f"reprocessed {name}")
    print(f"Reprocessed {len(documents)} document(s).")


def _restore_classification(document_id: object, classification: dict[str, object]) -> None:
    from app.services.classification import user_verified

    with SessionLocal() as db:
        document = db.get(Document, document_id)
        type_id = classification.get("document_type")
        if document is None or not isinstance(type_id, str):
            return
        result = user_verified(type_id)
        document.classification = classification
        document.document_type = result.display_name
        document.document_type_id = result.document_type
        document.category = result.category
        db.commit()


if __name__ == "__main__":
    main()
