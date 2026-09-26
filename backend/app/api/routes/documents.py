import uuid
from typing import Annotated, Any, Literal
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import current_user, require_document_access
from app.core.errors import AppError, NotFoundError, ValidationError
from app.db.session import get_db
from app.models import Clause, Document, DocumentStatus, LegalFact
from app.schemas.documents import (
    AnswerOut,
    AskIn,
    ClassificationIn,
    ConceptOut,
    ConceptSummary,
    DocumentOut,
    DocumentTypeOut,
    FactOut,
    OverviewOut,
    ProfessionalQuestionOut,
    QuestionsOut,
    SearchOut,
    SearchResultOut,
    SourceRef,
)
from app.services import audit, concepts, jobs, qa, questions, search, storage, taxonomy
from app.services.classification import user_verified
from app.services.normalize import build_normalized_document

router = APIRouter(
    prefix="/documents", tags=["documents"], dependencies=[Depends(require_document_access)]
)

DbSession = Annotated[Session, Depends(get_db)]
RECENT_DOCUMENTS_LIMIT = 50
OVERVIEW_CONCEPT_ORDER = [
    "notice_period", "probation", "time_limits", "important_dates", "effective_date", "duration",
    "salary", "rent", "deposit", "payment", "late_fee", "interest_rate", "job_title",
    "working_hours", "leave", "area", "notes", "eligibility", "documents_required", "termination",
    "renewal", "penalty", "cure_period", "appeal", "authority", "contact", "reference_number",
    "court_name", "case_number", "rights", "obligations", "governing_law", "jurisdiction",
    "arbitration", "dispute_resolution", "confidentiality", "intellectual_property",
    "non_compete", "non_solicitation", "indemnification", "liability", "force_majeure",
    "assignment",
]  # fmt: skip
QUESTIONS_INTRO = (
    "Questions you may want to discuss with a qualified legal professional. "
    "These are prompts for a conversation, not legal advice."
)


def _get_document(db: Session, document_id: uuid.UUID) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise NotFoundError("This document doesn't exist or has been deleted.")
    return document


def get_ready_document(db: Session, document_id: uuid.UUID) -> Document:
    document = _get_document(db, document_id)
    if document.status != DocumentStatus.READY:
        raise AppError(
            409,
            "document_not_ready",
            "This document is still being processed. Please wait a moment and try again.",
        )
    return document


def _fact_out(fact: LegalFact) -> FactOut:
    return FactOut(
        concept=fact.concept,
        label=concepts.CONCEPTS[fact.concept].label,
        value=fact.value,
        source=SourceRef(
            page_number=fact.page_number, clause_ref=fact.clause_ref, quote=fact.source_text
        ),
    )


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    db: DbSession,
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File()],
) -> Document:
    stored_filename, size, fmt = await storage.save_upload(file)
    document = Document(
        original_filename=storage.safe_display_name(file.filename),
        stored_filename=stored_filename,
        file_size=size,
        user_id=current_user(request).id,
        format=fmt,
        status=DocumentStatus.UPLOADED,
        status_detail="Waiting to be processed",
    )
    db.add(document)
    db.flush()
    audit.record(db, audit.UPLOAD, user_id=document.user_id, document_id=document.id,
                 request=request, detail={"file_size": size})  # fmt: skip
    db.commit()
    jobs.enqueue(background_tasks, document.id)
    return document


@router.get("", response_model=list[DocumentOut])
def list_documents(request: Request, db: DbSession) -> list[Document]:
    return list(
        db.scalars(
            select(Document)
            .where(Document.user_id == current_user(request).id)
            .order_by(Document.created_at.desc())
            .limit(RECENT_DOCUMENTS_LIMIT)
        )
    )


@router.get("/concepts", response_model=list[ConceptOut])
def list_concepts() -> list[ConceptOut]:
    return [ConceptOut(key=c.key, label=c.label) for c in concepts.CONCEPTS.values()]


@router.get("/types", response_model=list[DocumentTypeOut])
def list_document_types() -> list[DocumentTypeOut]:
    """All taxonomy document types, for the "choose the document type" picker."""
    names = taxonomy.category_names()
    return [
        DocumentTypeOut(id=t["id"], name=t["name"], category=t["category"],
                        category_name=names[t["category"]])
        for t in taxonomy.document_types()
        if t["id"] != "other.unknown"
    ]  # fmt: skip


@router.put("/{document_id}/classification", response_model=DocumentOut)
def set_classification(
    document_id: uuid.UUID, body: ClassificationIn, db: DbSession, request: Request
) -> Document:
    """The user confirms or corrects the document type. Stored as user_verified."""
    document = _get_document(db, document_id)
    try:
        result = user_verified(body.document_type_id)
    except ValueError as error:
        raise ValidationError(
            "unknown_document_type",
            "That document type doesn't exist. Please pick one from the list.",
        ) from error
    previous = document.classification or {}
    stored = result.to_json()
    if previous.get("document_type") and previous.get("status") != "user_verified":
        stored["alternatives"] = [
            {
                "document_type": previous["document_type"],
                "confidence": previous.get("confidence", 0),
            }
        ]
    document.classification = stored
    document.document_type = result.display_name
    document.document_type_id = result.document_type
    document.category = result.category
    audit.record(db, audit.CHANGE_TYPE, user_id=document.user_id, document_id=document.id,
                 request=request, detail={"document_type_id": body.document_type_id})  # fmt: skip
    db.commit()
    return document


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: uuid.UUID, db: DbSession) -> Document:
    return _get_document(db, document_id)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: uuid.UUID, db: DbSession, request: Request) -> None:
    document = _get_document(db, document_id)
    stored_filename = document.stored_filename
    audit.record(db, audit.DELETE, user_id=document.user_id, document_id=document.id,
                 request=request)  # fmt: skip
    db.delete(document)
    db.commit()
    storage.delete_file(stored_filename)


@router.get("/{document_id}/file")
def get_document_file(
    document_id: uuid.UUID, db: DbSession, request: Request, download: bool = False
) -> Response:
    """The original PDF (decrypted on the fly). With ?download=true the browser saves it."""
    document = _get_document(db, document_id)
    try:
        data = storage.read_file(document.stored_filename)
    except FileNotFoundError as error:
        raise NotFoundError("The original PDF file is missing. Please upload it again.") from error
    action = audit.DOWNLOAD_FILE if download else audit.VIEW_FILE
    audit.record(db, action, user_id=document.user_id, document_id=document.id, request=request)
    db.commit()
    disposition = "attachment" if download else "inline"
    filename = quote(document.original_filename)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"{disposition}; filename*=utf-8''{filename}",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{document_id}/normalized")
def get_normalized_document(document_id: uuid.UUID, db: DbSession) -> dict[str, Any]:
    """The document in the common normalized structure
    (data/schemas/normalized_document.schema.json), with every fact's source evidence."""
    return build_normalized_document(db, get_ready_document(db, document_id))


@router.get("/{document_id}/overview", response_model=OverviewOut)
def get_overview(document_id: uuid.UUID, db: DbSession) -> OverviewOut:
    document = get_ready_document(db, document_id)
    facts = db.scalars(
        select(LegalFact)
        .where(LegalFact.document_id == document_id)
        .order_by(LegalFact.page_number, LegalFact.id)
    ).all()
    clause_count = (
        db.scalar(select(func.count()).select_from(Clause).where(Clause.document_id == document_id))
        or 0
    )

    grouped: dict[str, list[FactOut]] = {}
    for fact in facts:
        grouped.setdefault(fact.concept, []).append(_fact_out(fact))
    summaries = [
        ConceptSummary(concept=key, label=concepts.CONCEPTS[key].label, facts=grouped[key])
        for key in OVERVIEW_CONCEPT_ORDER
        if key in grouped
    ]
    return OverviewOut(
        document=DocumentOut.model_validate(document),
        clause_count=clause_count,
        concepts=summaries,
        counts={
            "pages": document.page_count or 0,
            "clauses": clause_count,
            "dates": len(grouped.get("important_dates", [])) + len(grouped.get("time_limits", [])),
            "payments": len(grouped.get("payment", [])),
            "attention": sum(len(grouped.get(k, [])) for k in ("penalty", "liability")),
        },
    )


@router.get("/{document_id}/search", response_model=SearchOut)
def search_document(
    document_id: uuid.UUID,
    db: DbSession,
    q: Annotated[str, Query(min_length=1, max_length=300)],
    mode: Literal["exact", "semantic", "hybrid"] = "hybrid",
) -> SearchOut:
    get_ready_document(db, document_id)
    corrected = search.correct_query(db, document_id, q)
    used = q
    if mode == "exact":
        hits = search.exact_search(db, document_id, q)
        if not hits and corrected != q:
            hits, used = search.exact_search(db, document_id, corrected), corrected
    else:
        used = corrected
        find = search.semantic_search if mode == "semantic" else search.hybrid_search
        hits, _ = find(db, document_id, corrected)
    return SearchOut(
        query=q,
        corrected_query=used if used != q else None,
        mode=mode,
        results=[
            SearchResultOut(
                page_number=h.chunk.page_number,
                clause_ref=h.chunk.clause_ref,
                heading=h.chunk.heading,
                snippet=h.snippet,
                highlight=h.highlight,
                score=h.score,
            )
            for h in hits
        ],
        facts=[_fact_out(f) for f in search.facts_for_query(db, document_id, corrected)],
        related_concepts=concepts.related_concepts(concepts.detect_query_concepts(corrected)),
    )


@router.post("/{document_id}/ask", response_model=AnswerOut)
def ask_document(document_id: uuid.UUID, body: AskIn, db: DbSession) -> AnswerOut:
    get_ready_document(db, document_id)
    conversation, message, answer = qa.ask(
        db, document_id, body.question.strip(), body.conversation_id
    )
    return AnswerOut(
        conversation_id=conversation.id,
        message_id=message.id,
        question=body.question,
        found=answer.found,
        answer=answer.answer,
        simple_explanation=answer.simple_explanation,
        why_it_matters=answer.why_it_matters,
        citations=[
            SourceRef(
                page_number=c.chunk.page_number,
                clause_ref=c.chunk.clause_ref,
                heading=c.chunk.heading,
                quote=c.quote,
            )
            for c in answer.citations
        ],
        related_concepts=answer.related_concepts,
        generated_by=answer.generated_by,
        kind="about" if answer.kind == "about" else "document",
        points=answer.points,
        note=answer.note,
        searched_as=answer.searched_as,
    )


@router.get("/{document_id}/questions", response_model=QuestionsOut)
def professional_questions(document_id: uuid.UUID, db: DbSession) -> QuestionsOut:
    get_ready_document(db, document_id)
    facts = list(
        db.scalars(
            select(LegalFact)
            .where(LegalFact.document_id == document_id)
            .order_by(LegalFact.page_number)
        )
    )
    return QuestionsOut(
        intro=QUESTIONS_INTRO,
        questions=[
            ProfessionalQuestionOut(
                question=q.question,
                concept=q.concept,
                source=SourceRef(
                    page_number=q.fact.page_number,
                    clause_ref=q.fact.clause_ref,
                    quote=q.fact.source_text,
                ),
            )
            for q in questions.generate_questions(facts)
        ],
    )
