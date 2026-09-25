"""Re-run document classification for processed documents (e.g. after improving the rules).

Usage (from backend/):  uv run python -m scripts.reclassify [--all]

Documents the user classified themselves (status user_verified) are left alone unless --all.
"""

import argparse

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Clause, Document, DocumentPage, DocumentStatus
from app.services.classification import classify


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="also overwrite user-verified types")
    args = parser.parse_args()

    with SessionLocal() as db:
        documents = db.scalars(select(Document).where(Document.status == DocumentStatus.READY))
        changed = 0
        for document in documents:
            verified = (document.classification or {}).get("status") == "user_verified"
            if verified and not args.all:
                continue
            pages = list(
                db.scalars(
                    select(DocumentPage.text)
                    .where(DocumentPage.document_id == document.id)
                    .order_by(DocumentPage.page_number)
                )
            )
            headings = [
                h
                for h in db.scalars(select(Clause.heading).where(Clause.document_id == document.id))
                if h
            ]
            result = classify(pages, headings)
            document.document_type = result.display_name
            document.document_type_id = result.document_type
            document.category = result.category
            document.classification = result.to_json()
            changed += 1
            level = result.confidence_level
            print(f"{document.original_filename}: {result.display_name} ({level})")
        db.commit()
        print(f"Reclassified {changed} document(s).")


if __name__ == "__main__":
    main()
