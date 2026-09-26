import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.documents import get_ready_document
from app.core.auth import require_document_access
from app.core.errors import AppError, NotFoundError, ValidationError
from app.db.session import get_db
from app.models import Clause, Document, DocumentPage, DocumentStatus
from app.schemas.documents import (
    DocumentOut,
    IssueOut,
    IssuesOut,
    NotAppliedOut,
    RepairIn,
    RepairOut,
)
from app.services import audit, jobs, storage
from app.services.document_check import ClauseInfo, Issue, check_document
from app.services.repair import repair_pdf

router = APIRouter(
    prefix="/documents", tags=["document check"], dependencies=[Depends(require_document_access)]
)

DbSession = Annotated[Session, Depends(get_db)]
CORRECTED_SUFFIX = " (corrected)"


def document_issues(db: Session, document_id: uuid.UUID) -> list[Issue]:
    pages = db.scalars(
        select(DocumentPage.text)
        .where(DocumentPage.document_id == document_id)
        .order_by(DocumentPage.page_number)
    ).all()
    clauses = db.execute(
        select(Clause.page_number, Clause.clause_ref)
        .where(Clause.document_id == document_id)
        .order_by(Clause.page_number, Clause.id)
    ).all()
    return check_document(list(pages), [ClauseInfo(p, ref) for p, ref in clauses])


def _issue_out(issue: Issue) -> IssueOut:
    return IssueOut(
        id=issue.id,
        kind=issue.kind,
        label=issue.label,
        fixable=issue.fixable,
        page_number=issue.page_number,
        original=issue.original,
        suggestion=issue.suggestion,
        message=issue.message,
        context=issue.context,
    )


def _corrected_name(filename: str) -> str:
    path = Path(filename)
    return storage.safe_display_name(f"{path.stem}{CORRECTED_SUFFIX}{path.suffix or '.pdf'}")


@router.get("/{document_id}/issues", response_model=IssuesOut)
def list_issues(document_id: uuid.UUID, db: DbSession) -> IssuesOut:
    get_ready_document(db, document_id)
    issues = document_issues(db, document_id)
    return IssuesOut(
        fixable_count=sum(i.fixable for i in issues),
        review_count=sum(not i.fixable for i in issues),
        issues=[_issue_out(i) for i in issues],
    )


@router.post("/{document_id}/repair", response_model=RepairOut, status_code=status.HTTP_201_CREATED)
def repair_document(
    document_id: uuid.UUID,
    body: RepairIn,
    db: DbSession,
    background_tasks: BackgroundTasks,
    request: Request,
) -> RepairOut:
    """Create a corrected copy with the selected fixes. The original is never changed."""
    source = get_ready_document(db, document_id)
    by_id = {issue.id: issue for issue in document_issues(db, document_id)}
    selected = [by_id[i] for i in dict.fromkeys(body.issue_ids) if i in by_id]
    if not selected:
        raise ValidationError(
            "issues_changed",
            "These suggestions are no longer valid. Run the check again and choose the fixes.",
        )
    if not any(issue.fixable for issue in selected):
        raise ValidationError(
            "nothing_to_fix",
            "None of the selected items can be changed automatically. They need your review.",
        )

    try:
        original = storage.read_file(source.stored_filename)
    except FileNotFoundError as error:
        raise NotFoundError("The original PDF file is missing. Please upload it again.") from error
    result, corrected_pdf = repair_pdf(original, selected)
    if not result.applied:
        raise AppError(
            422,
            "repair_failed",
            "None of the selected fixes could be applied to this PDF. The text may be stored "
            "in a way that can't be edited safely.",
        )

    stored_filename = storage.new_stored_filename()
    storage.write_file(stored_filename, corrected_pdf)
    corrected = Document(
        original_filename=_corrected_name(source.original_filename),
        stored_filename=stored_filename,
        file_size=len(corrected_pdf),
        status=DocumentStatus.UPLOADED,
        status_detail="Waiting to be processed",
        source_document_id=source.id,
        user_id=source.user_id,
        changes=[
            {
                "page_number": issue.page_number,
                "kind": issue.kind,
                "original": issue.original,
                "replacement": issue.suggestion,
            }
            for issue in result.applied
        ],
    )
    db.add(corrected)
    db.flush()
    audit.record(
        db,
        audit.REPAIR,
        user_id=source.user_id,
        document_id=source.id,
        request=request,
        detail={"corrected_copy": str(corrected.id), "fixes": len(result.applied)},
    )
    db.commit()
    jobs.enqueue(background_tasks, corrected.id)
    return RepairOut(
        document=DocumentOut.model_validate(corrected),
        applied=[_issue_out(i) for i in result.applied],
        not_applied=[NotAppliedOut(issue=_issue_out(i), reason=r) for i, r in result.failed],
    )
