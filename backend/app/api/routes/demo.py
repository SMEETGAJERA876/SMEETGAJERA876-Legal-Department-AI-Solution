"""The public read-only demo (docs/Demo.md).

One endpoint, open to everyone: which documents anybody may open without signing in. The
documents themselves are read through the ordinary /documents routes — `require_document_access`
lets an anonymous visitor read a document flagged `is_demo` and refuses every write.

Nothing here touches a person's own documents, so there is no `require_document_access`
dependency on this router.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import Document, DocumentStatus
from app.schemas.documents import DemoDocumentOut, DemoOut

router = APIRouter(prefix="/demo", tags=["demo"])

DbSession = Annotated[Session, Depends(get_db)]

# Why each seeded document is worth opening, shown on the demo picker.
DESCRIPTIONS: dict[str, str] = {
    "consumer_protection_act_2019.pdf": (
        "A real Act of Parliament, 42 pages, as published on India Code. Ask what you can do "
        "about a defective product — and something it doesn't cover, to see it say so. Every "
        "answer can be read back in everyday words."
    ),
    "employment_agreement.pdf": (
        "A short employment contract. Notice period, probation, salary and what happens if you "
        "leave early — every answer points at the page."
    ),
    "rental_agreement_with_mistakes.pdf": (
        "A rental agreement with deliberate mistakes in it. Open Mistakes to see them found with "
        "a suggested fix, then Format to see what a registrable rent agreement is missing "
        "— stamp duty, signatures and witnesses."
    ),
}

SUGGESTED_QUESTIONS: dict[str, list[str]] = {
    "consumer_protection_act_2019.pdf": [
        "How many days do I have to appeal against the District Commission's order?",
        "What can I do if a product I bought is defective?",
        "What is the penalty for drunk driving?",
    ],
    "employment_agreement.pdf": [
        "What is my notice period?",
        "What happens if I leave within the first year?",
        "How long is the probation period?",
    ],
    "rental_agreement_with_mistakes.pdf": [
        "How much is the security deposit?",
        "How much notice do I have to give before leaving?",
    ],
}


@router.get("", response_model=DemoOut)
def list_demo_documents(db: DbSession) -> DemoOut:
    """Documents anyone may open without signing in. Empty when the demo is turned off."""
    if not get_settings().demo_mode_enabled:
        return DemoOut(enabled=False, documents=[])
    documents = db.scalars(
        select(Document)
        .where(Document.is_demo.is_(True), Document.status == DocumentStatus.READY)
        .order_by(Document.created_at)
    ).all()
    return DemoOut(
        enabled=True,
        documents=[
            DemoDocumentOut(
                id=document.id,
                original_filename=document.original_filename,
                document_type=document.document_type,
                page_count=document.page_count,
                description=DESCRIPTIONS.get(document.original_filename, ""),
                questions=SUGGESTED_QUESTIONS.get(document.original_filename, []),
            )
            for document in documents
        ],
    )
