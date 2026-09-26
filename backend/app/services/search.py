"""Exact and semantic search over a document's chunks."""

import re
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, literal_column, or_, select, text
from sqlalchemy.orm import Session

from app.models import DocumentChunk, LegalFact
from app.services import answerability, concepts, embeddings, glossary, reranker
from app.services.text_utils import normalize_whitespace, snippet_around, split_sentences

MAX_EXACT_RESULTS = 50
SEMANTIC_CANDIDATES = 24
CONCEPT_BOOST = 0.03
MAX_CONCEPT_BOOST = 0.09
FACT_BOOST = 0.06  # chunk contains an extracted fact for a concept the question is about
PRIMARY_FACT_BOOST = 0.04  # ...and extra when it's the concept the question names first
HEADING_BOOST = 0.03  # the clause heading fits the topic ("Termination" for notice questions)
# Hybrid search (docs/AI_Pipeline.md §3)
KEYWORD_CANDIDATES = 24
KEYWORD_WEIGHT = 0.08  # full-text relevance, scaled 0..1 within the candidates
LITERAL_BOOST = 0.06  # the chunk contains the query text itself ("1800-000-0000")
STRUCTURE_BOOST = 0.3  # the question names this clause ("Clause 13", "Rule 7")
MAX_ALIAS_CONCEPTS = 1  # only the concept the question names first
RERANK_POOL = 12  # candidates the cross-encoder re-orders
GLOSSARY_BOOST = 0.05  # the chunk uses the legal wording of the question's everyday words
HEADING_MATCH_WEIGHT = 3.0  # cross-encoder points for a heading fully covered by the question
MIN_LITERAL_CHARS = 4
_CLAUSE_REFERENCE = re.compile(
    r"\b(?P<kw>clause|section|rule|article|para(?:graph)?|chapter)\s+"
    r"(?P<num>\d{1,3}(?:\.\d{1,3})*|[ivxlc]{1,6})\b",
    re.IGNORECASE,
)


@dataclass
class SearchHit:
    chunk: DocumentChunk
    snippet: str
    highlight: str
    score: float | None = None
    concept_hits: int = 0  # how strongly the chunk relates to the question's legal concepts
    relevance: float | None = None  # cross-encoder score (reranker.py); None when it is off


_vocabulary_cache: dict[uuid.UUID, set[str]] = {}
MAX_CACHED_VOCABULARIES = 64
MIN_VOCABULARY_WORD_LENGTH = 3


def document_vocabulary(db: Session, document_id: uuid.UUID) -> set[str]:
    """Lowercase words used in the document (cached; documents don't change once processed)."""
    if document_id not in _vocabulary_cache:
        if len(_vocabulary_cache) >= MAX_CACHED_VOCABULARIES:
            _vocabulary_cache.pop(next(iter(_vocabulary_cache)))
        words: set[str] = set()
        for text in db.scalars(
            select(DocumentChunk.text).where(DocumentChunk.document_id == document_id)
        ):
            words.update(
                w
                for w in re.findall(r"[a-z]+", text.lower())
                if len(w) >= MIN_VOCABULARY_WORD_LENGTH
            )
        _vocabulary_cache[document_id] = words
    return _vocabulary_cache[document_id]


def correct_query(db: Session, document_id: uuid.UUID, query: str) -> str:
    """Fix typos using the document's own words, e.g. "notice pperiod" → "notice period"."""
    return concepts.correct_spelling(query, document_vocabulary(db, document_id))


def facts_for_query(db: Session, document_id: uuid.UUID, query: str) -> list[LegalFact]:
    """Every extracted fact of the kind the query is about (notice period → all time limits,
    notices and notes), in document order within each kind."""
    family = concepts.search_family(concepts.detect_query_concepts(query)[:1])
    if not family:
        return []
    facts = db.scalars(
        select(LegalFact)
        .where(LegalFact.document_id == document_id, LegalFact.concept.in_(family))
        .order_by(LegalFact.page_number, LegalFact.id)
    ).all()
    return sorted(facts, key=lambda f: family.index(f.concept))


def _like_pattern(query: str) -> str:
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def exact_search(db: Session, document_id: uuid.UUID, query: str) -> list[SearchHit]:
    query = normalize_whitespace(query)
    rows = db.scalars(
        select(DocumentChunk)
        .where(
            DocumentChunk.document_id == document_id,
            DocumentChunk.text.ilike(_like_pattern(query), escape="\\"),
        )
        .order_by(DocumentChunk.chunk_index)
    ).all()

    pattern = re.compile(re.escape(query), re.IGNORECASE)
    hits: list[SearchHit] = []
    for chunk in rows[:MAX_EXACT_RESULTS]:
        match = pattern.search(chunk.text)
        if match is None:  # ILIKE and regex can disagree on unusual characters
            continue
        hits.append(
            SearchHit(
                chunk=chunk,
                snippet=snippet_around(chunk.text, match.start(), match.end()),
                highlight=match.group(0),
            )
        )
    return hits


_sentence_vectors: dict[str, list[float]] = {}
MAX_CACHED_SENTENCES = 20_000


def _sentence_embeddings(sentences: list[str]) -> list[list[float]]:
    """Embeddings for many sentences in one model call; repeated sentences come from a cache."""
    missing = list(dict.fromkeys(s for s in sentences if s not in _sentence_vectors))
    if missing:
        if len(_sentence_vectors) + len(missing) > MAX_CACHED_SENTENCES:
            _sentence_vectors.clear()
        _sentence_vectors.update(zip(missing, embeddings.embed_passages(missing), strict=True))
    return [_sentence_vectors[s] for s in sentences]


def best_sentences(texts: list[str], query_vector: list[float] | None, query: str) -> list[str]:
    """For each chunk, the sentence that best matches the query (used for highlighting)."""
    literal = normalize_whitespace(query).lower()
    concept_keys = concepts.detect_query_concepts(query)
    choices: list[str | None] = []
    pending: list[tuple[int, list[str]]] = []  # chunks that need the embedding model
    for index, chunk_text in enumerate(texts):
        sentences = split_sentences(chunk_text)
        containing = (
            [s for s in sentences if literal in s.lower()]
            if len(literal) >= MIN_LITERAL_CHARS
            else []
        )
        if len(sentences) <= 1:
            choices.append(chunk_text)
        elif containing:
            choices.append(containing[0])  # an exact term the user typed wins
        elif query_vector is None:
            hits = concepts.concept_keyword_hits
            choices.append(max(sentences, key=lambda s: hits(s, concept_keys)))
        else:
            choices.append(None)
            pending.append((index, sentences))

    if query_vector is not None and pending:
        vectors = iter(_sentence_embeddings([s for _, sentences in pending for s in sentences]))
        for index, sentences in pending:
            scores = [
                sum(a * b for a, b in zip(next(vectors), query_vector, strict=True))
                + min(
                    CONCEPT_BOOST * concepts.concept_keyword_hits(s, concept_keys),
                    MAX_CONCEPT_BOOST,
                )
                for s in sentences
            ]
            choices[index] = sentences[max(range(len(sentences)), key=scores.__getitem__)]
    return [c if c is not None else t for c, t in zip(choices, texts, strict=True)]


def best_sentence(text: str, query_vector: list[float] | None, query: str) -> str:
    """Pick the sentence in a chunk that best matches the query (used for highlighting)."""
    return best_sentences([text], query_vector, query)[0]


def semantic_search(
    db: Session, document_id: uuid.UUID, query: str, limit: int = 8
) -> tuple[list[SearchHit], list[float]]:
    """Rank chunks by meaning, with a small boost for matching legal-concept vocabulary."""
    query_vector = embeddings.embed_query(query)
    distance = DocumentChunk.embedding.cosine_distance(query_vector)
    rows = db.execute(
        select(DocumentChunk, distance.label("distance"))
        .where(DocumentChunk.document_id == document_id, DocumentChunk.embedding.is_not(None))
        .order_by(distance)
        .limit(SEMANTIC_CANDIDATES)
    ).all()

    concept_keys = concepts.detect_query_concepts(query)
    chunks_with_facts = _chunks_with_facts(db, document_id, concept_keys)
    # The concept named most directly ("notice period" → notice_period) counts most.
    chunks_with_primary = _chunks_with_facts(db, document_id, concept_keys[:1])
    topic = concept_keys + concepts.related_concepts(concept_keys)
    scored = []
    for chunk, dist in rows:
        keyword_hits = concepts.concept_keyword_hits(chunk.text, concept_keys)
        has_fact = chunk.id in chunks_with_facts
        boost = (
            min(CONCEPT_BOOST * keyword_hits, MAX_CONCEPT_BOOST)
            + (FACT_BOOST if has_fact else 0)
            + (PRIMARY_FACT_BOOST if chunk.id in chunks_with_primary else 0)
            + (HEADING_BOOST if concepts.heading_matches(chunk.heading, topic) else 0)
        )
        scored.append((1.0 - float(dist) + boost, keyword_hits + int(has_fact), chunk))
    scored.sort(key=lambda item: item[0], reverse=True)

    top = scored[:limit]
    sentences = best_sentences([chunk.text for _, _, chunk in top], query_vector, query)
    hits = [
        SearchHit(chunk=chunk, snippet=sentence, highlight=sentence, score=score,
                  concept_hits=concept_hits)
        for (score, concept_hits, chunk), sentence in zip(top, sentences, strict=True)
    ]  # fmt: skip
    return hits, query_vector


def _chunks_with_facts(
    db: Session, document_id: uuid.UUID, concept_keys: list[str]
) -> set[uuid.UUID]:
    if not concept_keys:
        return set()
    return {
        chunk_id
        for chunk_id in db.scalars(
            select(LegalFact.chunk_id).where(
                LegalFact.document_id == document_id, LegalFact.concept.in_(concept_keys)
            )
        )
        if chunk_id is not None
    }


# ---------------------------------------------------------------- hybrid search


def _lexemes(db: Session, text_to_parse: str) -> list[str]:
    """Words as PostgreSQL's English parser indexes them (stemmed, stop words removed)."""
    if not text_to_parse.strip():
        return []
    result = db.execute(
        text("SELECT tsvector_to_array(to_tsvector('english', :t))"), {"t": text_to_parse}
    ).scalar()
    return list(result or [])


def _quote(lexeme: str) -> str:
    return "'" + lexeme.replace("'", "''") + "'"


def _phrase(db: Session, phrase: str) -> str | None:
    """A phrase query in reading order ("written notice" → 'written' <-> 'notic')."""
    result = db.execute(
        text("SELECT phraseto_tsquery('english', :t)::text"), {"t": phrase}
    ).scalar()
    return str(result) if result else None


def build_keyword_query(
    db: Session, query: str, concept_keys: list[str], legal_terms: list[str] | None = None
) -> str | None:
    """An OR tsquery: the question's own words, aliases of the concept it names first, and the
    legal wording of its everyday words (glossary). Multi-word terms become phrases."""
    parts = [_quote(lexeme) for lexeme in _lexemes(db, query)]
    terms = [
        a for key in concept_keys[:MAX_ALIAS_CONCEPTS] for a in concepts.CONCEPTS[key].keywords
    ]
    for alias in terms + (legal_terms or []):
        if " " in alias.strip():
            if phrase := _phrase(db, alias):
                parts.append(f"({phrase})")
        else:
            parts += [_quote(lexeme) for lexeme in _lexemes(db, alias)]
    unique = list(dict.fromkeys(parts))
    return " | ".join(unique) if unique else None


def _structure_filter(query: str) -> list[Any]:
    """SQL conditions matching clauses the question names: "Clause 13" → 13, 13.1, 13(a) …"""
    conditions: list[Any] = []
    for match in _CLAUSE_REFERENCE.finditer(query):
        number = match.group("num")
        keyword = match.group("kw").lower()
        label = "Para" if keyword.startswith("para") else keyword.capitalize()
        refs = [number] if keyword == "clause" else [f"{label} {number}", number]
        for ref in refs:
            conditions += [
                DocumentChunk.clause_ref == ref,
                DocumentChunk.clause_ref.like(f"{ref}.%"),
                DocumentChunk.clause_ref.like(f"{ref}(%"),
            ]
    return conditions


_SECTION_NUMBER = re.compile(r"^(?:[A-Za-z]+\s+)?(\d+[A-Z]*|[IVXLC]+)")
_STEM_WORD = re.compile(r"[a-z]{3,}")
MIN_HEADING_STEM = 4


def _stem(word: str) -> str:
    return word[: max(MIN_HEADING_STEM, len(word) - 3)]


def _content_stems(text: str) -> set[str]:
    return {_stem(w) for w in _STEM_WORD.findall(text.lower()) if w not in answerability.GENERIC}


def _heading_overlap(subject: set[str], heading: str | None) -> float:
    """Share of the heading's content words that the question (or its legal wording) uses."""
    if not heading or not subject:
        return 0.0
    words = _content_stems(heading)
    return len(words & subject) / len(words) if words else 0.0


def _section_key(chunk: DocumentChunk) -> str:
    match = _SECTION_NUMBER.match(chunk.clause_ref or "")
    return match.group(1) if match else str(chunk.id)


def _one_per_section_first(
    ranked: list[tuple[float, int, DocumentChunk]],
) -> list[tuple[float, int, DocumentChunk]]:
    """Best passage of each section first, then the remaining passages: five results from
    five different sections beat five passages of one."""
    seen: set[str] = set()
    first: list[tuple[float, int, DocumentChunk]] = []
    rest: list[tuple[float, int, DocumentChunk]] = []
    for item in ranked:
        key = _section_key(item[2])
        (rest if key in seen else first).append(item)
        seen.add(key)
    return first + rest


def hybrid_search(
    db: Session, document_id: uuid.UUID, query: str, limit: int = 8
) -> tuple[list[SearchHit], list[float]]:
    """Meaning + keywords + legal concepts + document structure (spec §27).

    Candidates come from the semantic list, the full-text list and any clause the question
    names. Each is scored on the cosine-similarity scale (so "not found" thresholds keep their
    meaning) plus keyword relevance, literal matches, concept/fact evidence and structure.
    """
    query_vector = embeddings.embed_query(query)
    concept_keys = concepts.detect_query_concepts(query)
    legal_terms = glossary.legal_terms(query)
    legal_phrases = [t.lower() for t in legal_terms if " " in t]
    keyword_query = build_keyword_query(db, query, concept_keys, legal_terms)
    distance = DocumentChunk.embedding.cosine_distance(query_vector).label("distance")
    tsquery = func.to_tsquery(literal_column("'simple'::regconfig"), keyword_query or "")
    rank = (
        func.ts_rank_cd(DocumentChunk.search_vector, tsquery)
        if keyword_query
        else literal_column("0.0")
    ).label("rank")
    base = select(DocumentChunk, distance, rank).where(
        DocumentChunk.document_id == document_id, DocumentChunk.embedding.is_not(None)
    )

    rows = list(db.execute(base.order_by(distance).limit(SEMANTIC_CANDIDATES)))
    if keyword_query:
        rows += db.execute(
            base.where(DocumentChunk.search_vector.op("@@")(tsquery))
            .order_by(rank.desc())
            .limit(KEYWORD_CANDIDATES)
        )
    structure = _structure_filter(query)
    structural_ids: set[uuid.UUID] = set()
    if structure:
        structural = list(db.execute(base.where(or_(*structure))))
        structural_ids = {chunk.id for chunk, _, _ in structural}
        rows += structural

    candidates: dict[uuid.UUID, tuple[DocumentChunk, float, float]] = {}
    for chunk, dist, keyword_rank in rows:
        candidates[chunk.id] = (chunk, float(dist), float(keyword_rank or 0.0))
    max_rank = max((r for _, _, r in candidates.values()), default=0.0) or 1.0

    chunks_with_facts = _chunks_with_facts(db, document_id, concept_keys)
    chunks_with_primary = _chunks_with_facts(db, document_id, concept_keys[:1])
    topic = concept_keys + concepts.related_concepts(concept_keys)
    literal = normalize_whitespace(query).lower()
    scored = []
    for chunk, dist, keyword_rank in candidates.values():
        keyword_hits = concepts.concept_keyword_hits(chunk.text, concept_keys)
        has_fact = chunk.id in chunks_with_facts
        score = (
            1.0
            - dist
            + KEYWORD_WEIGHT * keyword_rank / max_rank
            + (
                LITERAL_BOOST
                if len(literal) >= MIN_LITERAL_CHARS and literal in chunk.text.lower()
                else 0
            )
            + min(CONCEPT_BOOST * keyword_hits, MAX_CONCEPT_BOOST)
            + (FACT_BOOST if has_fact else 0)
            + (PRIMARY_FACT_BOOST if chunk.id in chunks_with_primary else 0)
            + (HEADING_BOOST if concepts.heading_matches(chunk.heading, topic) else 0)
            + (STRUCTURE_BOOST if chunk.id in structural_ids else 0)
            + (GLOSSARY_BOOST if any(p in chunk.text.lower() for p in legal_phrases) else 0)
        )
        scored.append((score, keyword_hits + int(has_fact), chunk))
    scored.sort(key=lambda item: item[0], reverse=True)

    # Second stage: a cross-encoder re-orders the best candidates. A clause the question names
    # ("Section 7") stays on top.
    relevance: dict[uuid.UUID, float] = {}
    if reranker.enabled() and scored:
        pool = scored[:RERANK_POOL]
        passages = [f"{c.heading}: {c.text}" if c.heading else c.text for _, _, c in pool]
        # The cross-encoder also sees the legal wording of the question's everyday words.
        rerank_query = f"{query} ({'; '.join(legal_terms)})" if legal_terms else query
        relevance = dict(
            zip((c.id for _, _, c in pool), reranker.scores(rerank_query, passages), strict=True)
        )
        # Section headings in statutes and contracts are precise summaries ("Punishment for
        # identity theft"): a question that uses the heading's words gets a lift.
        subject = _content_stems(f"{query} {' '.join(legal_terms)}")
        for _, _, chunk in pool:
            relevance[chunk.id] += HEADING_MATCH_WEIGHT * _heading_overlap(subject, chunk.heading)
        pool.sort(
            key=lambda item: (item[2].id in structural_ids, relevance[item[2].id]), reverse=True
        )
        scored = _one_per_section_first(pool)

    top = scored[:limit]
    sentences = best_sentences([chunk.text for _, _, chunk in top], query_vector, query)
    hits = [
        SearchHit(chunk=chunk, snippet=sentence, highlight=sentence, score=score,
                  concept_hits=concept_hits, relevance=relevance.get(chunk.id))
        for (score, concept_hits, chunk), sentence in zip(top, sentences, strict=True)
    ]  # fmt: skip
    return hits, query_vector
