import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import DocumentStatus


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    file_size: int
    format: str
    page_count: int | None
    status: DocumentStatus
    status_detail: str | None
    error_message: str | None
    document_type: str | None  # display name, e.g. "Employment Agreement"
    document_type_id: str | None = None  # taxonomy id, e.g. employment.employment_agreement
    category: str | None = None
    classification: dict[str, Any] | None = None
    parties: list[str]
    created_at: datetime
    processed_at: datetime | None
    source_document_id: uuid.UUID | None = None
    changes: list[dict[str, Any]] = []
    # Part of the public read-only demo: the website hides anything that would change it.
    is_demo: bool = False


class SourceRef(BaseModel):
    page_number: int
    clause_ref: str | None
    heading: str | None = None
    quote: str


class FactOut(BaseModel):
    concept: str
    label: str
    value: str
    source: SourceRef


class ConceptSummary(BaseModel):
    concept: str
    label: str
    facts: list[FactOut]


class OverviewOut(BaseModel):
    document: DocumentOut
    clause_count: int
    concepts: list[ConceptSummary]
    counts: dict[str, int]


class SearchResultOut(BaseModel):
    page_number: int
    clause_ref: str | None
    heading: str | None
    snippet: str
    highlight: str
    score: float | None


class SearchOut(BaseModel):
    query: str
    corrected_query: str | None  # set when typos were fixed, e.g. "notice pperiod"
    mode: Literal["exact", "semantic", "hybrid"]
    results: list[SearchResultOut]
    facts: list[FactOut]  # every extracted fact of the kind being searched for
    related_concepts: list[str]


class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    conversation_id: uuid.UUID | None = None


class AnswerOut(BaseModel):
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    question: str
    found: bool
    answer: str
    simple_explanation: str | None
    why_it_matters: str | None
    citations: list[SourceRef]
    related_concepts: list[str]
    generated_by: str
    kind: Literal["document", "about"]
    points: list[str]
    note: str | None
    searched_as: str | None


class ProfessionalQuestionOut(BaseModel):
    question: str
    concept: str
    source: SourceRef


class QuestionsOut(BaseModel):
    intro: str
    questions: list[ProfessionalQuestionOut]


class ConceptOut(BaseModel):
    key: str
    label: str


class IssueOut(BaseModel):
    id: str
    kind: str
    label: str
    fixable: bool
    page_number: int
    original: str
    suggestion: str | None
    message: str
    context: str


class IssuesOut(BaseModel):
    fixable_count: int
    review_count: int
    issues: list[IssueOut]


class RepairIn(BaseModel):
    issue_ids: list[str] = Field(min_length=1, max_length=200)


class NotAppliedOut(BaseModel):
    issue: IssueOut
    reason: str


class RepairOut(BaseModel):
    document: DocumentOut
    applied: list[IssueOut]
    not_applied: list[NotAppliedOut]


class DocumentTypeOut(BaseModel):
    id: str
    name: str
    category: str
    category_name: str


class ClassificationIn(BaseModel):
    document_type_id: str = Field(min_length=3, max_length=80)


class DemoDocumentOut(BaseModel):
    """A document on the public demo picker (app/api/routes/demo.py)."""

    id: uuid.UUID
    original_filename: str
    document_type: str | None
    page_count: int | None
    description: str
    questions: list[str]


class DemoOut(BaseModel):
    enabled: bool
    documents: list[DemoDocumentOut]
