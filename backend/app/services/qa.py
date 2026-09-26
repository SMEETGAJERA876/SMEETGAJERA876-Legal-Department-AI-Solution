"""Retrieval-grounded question answering: Question → Retrieve → Context → Answer → Citation."""

import re
import uuid
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models import Citation, Clause, Conversation, Document, DocumentChunk, LegalFact, Message
from app.services import about, answerability, concepts, glossary, simplify
from app.services.ai_provider import ProviderAnswer, SourceExcerpt, get_chat_provider
from app.services.search import (
    SearchHit,
    correct_query,
    document_vocabulary,
    hybrid_search,
)
from app.services.text_utils import contains_quote, format_clause

RETRIEVAL_LIMIT = 6
HISTORY_MESSAGES = 6
# Below this similarity the extractive fallback treats the document as not answering
# (used only when the cross-encoder re-ranker is switched off).
MIN_EXTRACTIVE_SCORE = 0.62
# With the re-ranker: passages within this margin of the best one may supply the answer.
RELEVANCE_WINDOW = 3.0
# ...but a value ("two years") is only taken from a passage about as relevant as the best.
VALUE_RELEVANCE_WINDOW = 1.0
WIDE_VALUE_WINDOW = 5.0
_ENUMERATOR = re.compile(r"^\s*(?:\d+(?:\.\d+)*|\([a-z0-9]+\))[.)]?\s+", re.IGNORECASE)
_HAS_FIGURE = re.compile(
    r"\d|\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty"
    r"|thirty|forty|forty-five|fifty|sixty|ninety|hundred|thousand|lakh|crore)\b",
    re.IGNORECASE,
)
NOT_FOUND_MESSAGE = "I couldn't find enough information in the uploaded document to answer this."
# Concepts with concrete values, and how to describe several of them.
VALUE_CONCEPTS = {
    "notice_period": "notice periods",
    "probation": "probation periods",
    "duration": "time periods",
    "salary": "salary amounts",
    "rent": "rent amounts",
    "deposit": "deposits",
    "late_fee": "late fees",
    "interest_rate": "interest rates",
    "payment": "amounts",
    "important_dates": "dates",
    "effective_date": "effective dates",
    "time_limits": "time limits",
    "working_hours": "working hours",
    "leave": "leave entitlements",
    "job_title": "job titles",
    "area": "areas",
    "governing_law": "governing laws",
    "jurisdiction": "courts",
    "arbitration": "arbitration arrangements",
    "cure_period": "cure periods",
    "reference_number": "reference numbers",
    "contact": "contact details",
    "court_name": "courts",
    "case_number": "case numbers",
}
VALUE_SCORE_WINDOW = 0.08  # list other values only if they match about as well as the best


@dataclass
class AnswerCitation:
    chunk: DocumentChunk
    quote: str


@dataclass
class Answer:
    found: bool
    answer: str
    simple_explanation: str | None
    why_it_matters: str | None
    citations: list[AnswerCitation]
    related_concepts: list[str]
    generated_by: str
    kind: str = "document"  # "document" = from the uploaded file; "about" = about ClauseLens
    points: list[str] = field(default_factory=list)
    note: str | None = None
    searched_as: str | None = None  # the question after fixing typos, if it changed
    #: The everyday words in the question and the formal wording the document uses for them,
    #: as (plain, legal) — "you said 'builder'; this document says 'promoter'".
    matched_terms: list[tuple[str, str]] = field(default_factory=list)
    #: Formal terms the quoted wording uses, and what they mean, as (legal, plain).
    quoted_terms: list[tuple[str, str]] = field(default_factory=list)


def _conversation(
    db: Session, document_id: uuid.UUID, conversation_id: uuid.UUID | None
) -> Conversation:
    if conversation_id is not None:
        conversation = db.get(Conversation, conversation_id)
        if conversation is None or conversation.document_id != document_id:
            raise NotFoundError("This conversation no longer exists. Start a new question.")
        return conversation
    conversation = Conversation(document_id=document_id)
    db.add(conversation)
    db.flush()
    return conversation


def _history(conversation: Conversation) -> list[tuple[str, str]]:
    return [(m.role, m.content) for m in conversation.messages[-HISTORY_MESSAGES:]]


def _validated_citations(result: ProviderAnswer, hits: list[SearchHit]) -> list[AnswerCitation]:
    citations: list[AnswerCitation] = []
    for citation in result.citations:
        index = citation.source_id - 1
        if not 0 <= index < len(hits):
            continue  # cites an excerpt that doesn't exist
        chunk = hits[index].chunk
        quote = (
            citation.quote if contains_quote(chunk.text, citation.quote) else hits[index].highlight
        )
        if not any(c.chunk.id == chunk.id and c.quote == quote for c in citations):
            citations.append(AnswerCitation(chunk, quote))
    return citations


def _location(chunk: DocumentChunk) -> str:
    location = f"Page {chunk.page_number}"
    return f"{location}, {format_clause(chunk.clause_ref)}" if chunk.clause_ref else location


def _value_facts(
    db: Session, document_id: uuid.UUID, hits: list[SearchHit], concept_keys: list[str]
) -> list[tuple[LegalFact, SearchHit]]:
    """Facts with a concrete value (e.g. "90 days") found in the retrieved chunks, best first."""
    wanted = [k for k in concept_keys if k in VALUE_CONCEPTS]
    if not wanted:
        return []
    by_chunk = {h.chunk.id: h for h in hits}
    facts = db.scalars(
        select(LegalFact).where(
            LegalFact.document_id == document_id,
            LegalFact.concept.in_(wanted),
            LegalFact.chunk_id.in_(by_chunk),
        )
    ).all()
    topic = wanted + concepts.related_concepts(wanted)
    position = {h.chunk.id: i for i, h in enumerate(hits)}
    ranked = [(f, by_chunk[f.chunk_id]) for f in facts if f.chunk_id is not None]
    reranked = any(h.relevance is not None for h in hits)
    # A value under a fitting heading ("Termination") outranks one elsewhere ("Probation");
    # then the cross-encoder's order (or, without it, the hybrid score).
    ranked.sort(
        key=lambda pair: (
            concepts.heading_matches(pair[1].chunk.heading, topic),
            -position[pair[1].chunk.id] if reranked else pair[1].score or 0,
        ),
        reverse=True,
    )
    return ranked


def _extractive_answer(
    db: Session,
    document_id: uuid.UUID,
    question: str,
    hits: list[SearchHit],
    query_vector: list[float],
    concept_keys: list[str],
) -> Answer:
    """Answer without a generative model: only quote what the document says."""
    related = concepts.related_concepts(concept_keys)
    reranked = bool(hits) and hits[0].relevance is not None
    if reranked:
        # The cross-encoder already judged relevance (and answerability was checked).
        best = hits[0].relevance or 0.0
        relevant = [h for h in hits if (h.relevance or best) >= best - WIDE_VALUE_WINDOW]
    else:
        # If the question is about a known concept, only passages about that concept count.
        relevant = [
            h
            for h in hits
            if (h.score or 0) >= MIN_EXTRACTIVE_SCORE and (not concept_keys or h.concept_hits > 0)
        ]
    if not relevant:
        return Answer(False, NOT_FOUND_MESSAGE, None, None, [], related, "none")

    # Answer with values (e.g. "90 days") only from passages that match about as well as the
    # best one, preferring the concept the question names most directly (concept_keys order).
    min_score = (relevant[0].score or 0) - VALUE_SCORE_WINDOW
    # A value comes from a passage about as relevant as the best one — unless the best passage
    # has no figure at all ("salary in lieu of the notice period"), then from nearby ones too.
    body = _ENUMERATOR.sub("", relevant[0].chunk.text)
    window = VALUE_RELEVANCE_WINDOW if _HAS_FIGURE.search(body) else WIDE_VALUE_WINDOW
    min_relevance = (relevant[0].relevance or 0) - window
    close = [(f, h) for f, h in _value_facts(db, document_id, relevant, concept_keys)
             if ((h.relevance or 0) >= min_relevance if reranked
                 else (h.score or 0) >= min_score)]  # fmt: skip
    concept = next((k for k in concept_keys if any(f.concept == k for f, _ in close)), None)
    if concept is not None:
        value_facts = [(fact, hit) for fact, hit in close if fact.concept == concept][:3]
        parts = [f"{fact.value} ({_location(hit.chunk)})" for fact, hit in value_facts]
        if len(parts) == 1:
            label = concepts.CONCEPTS[concept].label
            answer = f"{label}: {parts[0]}, according to the document."
        else:
            answer = f"The document mentions these {VALUE_CONCEPTS[concept]}: " + "; ".join(parts)
        citations = [AnswerCitation(hit.chunk, fact.source_text) for fact, hit in value_facts]
    else:
        top = relevant[0]
        quote = top.highlight  # the sentence search already chose for this question
        answer = f"The most relevant part of the document ({_location(top.chunk)}) says: “{quote}”"
        citations = [AnswerCitation(top.chunk, quote)]
        floor = (top.relevance or 0) - RELEVANCE_WINDOW
        citations += [
            AnswerCitation(h.chunk, h.highlight)
            for h in relevant[1:3]
            if h.relevance is None or h.relevance >= floor
        ]

    return Answer(
        found=True,
        answer=answer,
        simple_explanation=None,
        why_it_matters=None,
        citations=citations,
        related_concepts=related,
        generated_by="none",
    )


def _about_answer(db: Session, document_id: uuid.UUID, question: str) -> Answer:
    document = db.get(Document, document_id)
    fact_count = db.scalar(
        select(func.count()).select_from(LegalFact).where(LegalFact.document_id == document_id)
    )
    clause_count = db.scalar(
        select(func.count()).select_from(Clause).where(Clause.document_id == document_id)
    )
    result = about.answer_about(
        question, document.page_count if document else None, fact_count or 0, clause_count or 0
    )
    return Answer(
        found=True,
        answer=result.answer,
        simple_explanation=None,
        why_it_matters=None,
        citations=[],
        related_concepts=[],
        generated_by="about",
        kind="about",
        points=result.points,
        note=result.note,
    )


def _document_answer(
    db: Session, document_id: uuid.UUID, question: str, history: list[tuple[str, str]]
) -> Answer:
    corrected = correct_query(db, document_id, question)
    hits, query_vector = hybrid_search(db, document_id, corrected, limit=RETRIEVAL_LIMIT)
    concept_keys = concepts.detect_query_concepts(corrected)
    provider = get_chat_provider()
    question = corrected

    best_relevance = hits[0].relevance if hits else None
    if not hits or not answerability.answerable(
        question, document_vocabulary(db, document_id), best_relevance
    ):
        related = concepts.related_concepts(concept_keys)
        return Answer(False, NOT_FOUND_MESSAGE, None, None, [], related, "none")

    excerpts = [
        SourceExcerpt(i, h.chunk.page_number, h.chunk.clause_ref, h.chunk.heading, h.chunk.text)
        for i, h in enumerate(hits, start=1)
    ]
    result = provider.answer(question, excerpts, history) if hits else None

    if result is None:
        answer = _extractive_answer(db, document_id, question, hits, query_vector, concept_keys)
    else:
        citations = _validated_citations(result, hits)
        found = result.found and bool(citations)  # uncited claims are not shown as facts
        answer = Answer(
            found=found,
            answer=result.answer if found else NOT_FOUND_MESSAGE,
            simple_explanation=result.simple_explanation if found else None,
            why_it_matters=result.why_it_matters if found else None,
            citations=citations if found else [],
            related_concepts=concepts.related_concepts(concept_keys),
            generated_by=provider.name,
        )
    return answer


def _worth_bridging(plain: str, legal: str) -> bool:
    """Whether "you said X, the document says Y" tells the reader anything.

    "builder" → "promoter" is worth saying. "complain" → "complaint" is the same word with an
    ending on it, and showing it makes the feature look like it is padding.
    """
    plain, legal = plain.casefold(), legal.casefold()
    if plain == legal:
        return False
    shorter, longer = sorted((plain, legal), key=len)
    return not longer.startswith(shorter)


def _add_plain_language(answer: Answer, question: str) -> None:
    """Say what the formal wording means, and which formal words the question mapped to.

    The simplifier is local and deterministic (services/simplify.py), so this works on a
    deployment with no AI key. When a provider already wrote an explanation, that one is kept.
    """
    if not answer.found or not answer.citations:
        return
    quote = answer.citations[0].quote
    result = simplify.simplified(quote)
    if answer.simple_explanation is None and result.worth_showing:
        answer.simple_explanation = result.simple
    answer.quoted_terms = result.terms

    # "builder" in the question → "promoter" in the Act, but only the pairs that the document
    # wording actually used, so we never claim a mapping the reader cannot see.
    quoted = " ".join(c.quote for c in answer.citations).casefold()
    plain_words = glossary.plain_phrases(question)
    matched: list[tuple[str, str]] = []
    for plain in plain_words:
        for legal in glossary.legal_terms(plain):
            if legal.casefold() in quoted and _worth_bridging(plain, legal):
                pair = (plain, legal)
                if pair not in matched:
                    matched.append(pair)
    answer.matched_terms = matched[:4]


def ask(
    db: Session, document_id: uuid.UUID, question: str, conversation_id: uuid.UUID | None
) -> tuple[Conversation, Message, Answer]:
    conversation = _conversation(db, document_id, conversation_id)
    if about.is_about_question(question):
        answer = _about_answer(db, document_id, question)
    else:
        answer = _document_answer(db, document_id, question, _history(conversation))
        corrected = correct_query(db, document_id, question)
        answer.searched_as = corrected if corrected != question else None
        _add_plain_language(answer, question)

    db.add(Message(conversation_id=conversation.id, role="user", content=question))
    message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer.answer,
        data={
            "found": answer.found,
            "simple_explanation": answer.simple_explanation,
            "why_it_matters": answer.why_it_matters,
            "related_concepts": answer.related_concepts,
            "generated_by": answer.generated_by,
            "kind": answer.kind,
            "points": answer.points,
            "matched_terms": answer.matched_terms,
            "quoted_terms": answer.quoted_terms,
        },
        citations=[
            Citation(
                chunk_id=c.chunk.id,
                page_number=c.chunk.page_number,
                clause_ref=c.chunk.clause_ref,
                quote=c.quote,
            )
            for c in answer.citations
        ],
    )
    db.add(message)
    db.commit()
    return conversation, message, answer
