import uuid
from pathlib import Path
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.routes.document_check import document_issues
from app.api.routes.documents import get_ready_document
from app.core.auth import require_document_access
from app.db.session import get_db
from app.models import Clause, LegalFact
from app.services import audit
from app.services.questions import generate_questions
from app.services.summary_pdf import SummaryInput, build_summary_pdf

router = APIRouter(
    prefix="/documents", tags=["summary"], dependencies=[Depends(require_document_access)]
)

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/{document_id}/summary", response_class=Response)
def download_summary(
    document_id: uuid.UUID, db: DbSession, request: Request, download: bool = True
) -> Response:
    """A one-file PDF summary: key dates, notice periods, deadlines, money, process details,
    items to review and questions for a legal professional — each with its page."""
    document = get_ready_document(db, document_id)
    facts = list(
        db.scalars(
            select(LegalFact)
            .where(LegalFact.document_id == document_id)
            .order_by(LegalFact.page_number, LegalFact.id)
        )
    )
    clause_count = db.scalar(
        select(func.count()).select_from(Clause).where(Clause.document_id == document_id)
    )
    title = Path(document.original_filename).stem.replace("_", " ")
    content = build_summary_pdf(
        SummaryInput(
            title=title,
            document_type=document.document_type,
            page_count=document.page_count or 0,
            clause_count=clause_count or 0,
            parties=document.parties,
            facts=facts,
            review_issues=[i for i in document_issues(db, document_id) if not i.fixable],
            questions=generate_questions(facts),
        )
    )
    audit.record(db, audit.DOWNLOAD_SUMMARY, user_id=document.user_id,
                 document_id=document.id, request=request)  # fmt: skip
    db.commit()
    disposition = "attachment" if download else "inline"
    filename = quote(f"{Path(document.original_filename).stem} - summary.pdf")
    return Response(
        content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"{disposition}; filename*=utf-8''{filename}",
            "X-Content-Type-Options": "nosniff",
        },
    )
