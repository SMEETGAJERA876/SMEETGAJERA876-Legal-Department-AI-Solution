"""Build the normalized document (data/schemas/normalized_document.schema.json) for a
processed document: Document → Page → Section → Clause → Concept → Fact → Source evidence.

Evidence offsets refer to the normalized page text (whitespace collapsed), which is what
`pages[].text` contains, so `pages[p].text[char_start:char_end] == source_text`.
"""

import re
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, DocumentChunk, DocumentPage, LegalFact
from app.services import taxonomy
from app.services.classification import Classification
from app.services.extraction import detect_party_roles
from app.services.normalized_values import normalize
from app.services.parsing import DocumentParseError, parse_file
from app.services.storage import read_file
from app.services.text_utils import normalize_whitespace

SCHEMA_VERSION = "1.0"
MIME_TYPES = {"pdf": "application/pdf"}

# Rule-based extraction confidence per engine concept (docs/AI_Pipeline.md §5).
FACT_CONFIDENCE = {
    "notice_period": 0.9, "time_limits": 0.85, "important_dates": 0.9, "duration": 0.85,
    "payment": 0.8, "notes": 0.7,
}  # fmt: skip
KEYWORD_FACT_CONFIDENCE = 0.6

SECTION_ROLES = [
    ("definition", "definitions"), ("termination", "termination"), ("notice", "notice"),
    ("eligib", "eligibility"), ("document", "required_documents"), ("appeal", "appeal"),
    ("contact", "contact"), ("salary", "compensation"), ("payment", "payment"), ("fee", "payment"),
    ("rent", "payment"), ("term", "term"), ("renewal", "renewal"), ("penalt", "penalty"),
    ("confidential", "confidentiality"), ("dispute", "dispute_resolution"),
    ("governing law", "governing_law"), ("liabilit", "liability"), ("note", "notes"),
    ("date", "important_dates"), ("probation", "probation"), ("duties", "responsibilities"),
    ("responsib", "responsibilities"), ("purpose", "purpose"), ("preliminary", "preliminary"),
]  # fmt: skip
_ORG_WORDS = re.compile(
    r"\b(limited|ltd|pvt|private|llp|inc|company|corporation|department|government|ministry|"
    r"authority|bank|university|board|trust)\b",
    re.IGNORECASE,
)


def classification_for(document: Document) -> dict[str, Any]:
    if document.classification:
        return dict(document.classification)
    return Classification(None, None, 0.0, "low", "unknown", signals=["not classified"]).to_json()


def _section_key(clause_ref: str | None, heading: str | None) -> str:
    if clause_ref is None:
        return f"heading:{heading or ''}"
    prefix, _, number = clause_ref.rpartition(" ")
    top = re.split(r"[.(]", number, maxsplit=1)[0]
    return f"{prefix} {top}".strip()


def _role(heading: str | None) -> str | None:
    lowered = (heading or "").lower()
    return next((role for needle, role in SECTION_ROLES if needle in lowered), None)


def _span(page_text: str, text: str, start: int = 0) -> tuple[int, int] | None:
    at = page_text.find(text, start)
    if at < 0:
        at = page_text.find(text)
    return (at, at + len(text)) if at >= 0 else None


def _entity_type(name: str) -> str:
    return "organization" if _ORG_WORDS.search(name) else "person"


def build_normalized_document(db: Session, document: Document) -> dict[str, Any]:
    pages = db.scalars(
        select(DocumentPage)
        .where(DocumentPage.document_id == document.id)
        .order_by(DocumentPage.page_number)
    ).all()
    chunks = db.scalars(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document.id)
        .order_by(DocumentChunk.chunk_index)
    ).all()
    facts = db.scalars(
        select(LegalFact)
        .where(LegalFact.document_id == document.id)
        .order_by(LegalFact.page_number, LegalFact.id)
    ).all()
    page_text = {p.page_number: normalize_whitespace(p.text) for p in pages}
    concept_ids = taxonomy.concept_id_for_engine_key()

    warnings = ["Language detection is not implemented yet; English is assumed."]
    parsed_pages: dict[int, Any] = {}
    parser_name, parser_version, is_scanned = "unknown", "unknown", False
    try:
        # Layout only: page text comes from the database, so scanned pages are not re-OCR'd.
        parsed = parse_file(read_file(document.stored_filename), document.format, ocr=False)
        parsed_pages = {p.page_number: p for p in parsed.pages}
        parser_name, parser_version, is_scanned = (
            parsed.parser,
            parsed.parser_version,
            parsed.is_scanned,
        )
        warnings += parsed.warnings
    except (DocumentParseError, OSError):
        warnings.append("The original file could not be re-read; page layout (blocks) is omitted.")

    fact_json, facts_by_chunk = _facts(facts, chunks, page_text, concept_ids)
    return {
        "schema_version": SCHEMA_VERSION,
        "document": _document(document, len(pages), is_scanned),
        "parties": _parties(document, page_text),
        "pages": [
            _page(p.page_number, page_text[p.page_number], parsed_pages.get(p.page_number))
            for p in pages
        ],  # fmt: skip
        "sections": _sections(chunks, page_text, facts_by_chunk),
        "facts": fact_json,
        "entities": [
            {"id": f"E{i}", "type": _entity_type(n), "text": n, "mentions": [{"page_number": 1}]}
            for i, n in enumerate(document.parties, start=1)
        ],
        "processing": {
            "parser": parser_name,
            "parser_version": parser_version,
            "ocr_used": False,
            "taxonomy_version": taxonomy.taxonomy_version(),
            **(
                {"processed_at": document.processed_at.isoformat()} if document.processed_at else {}
            ),
            "warnings": warnings,
        },
    }


def _parties(document: Document, page_text: dict[int, str]) -> list[dict[str, Any]]:
    """Parties with their role ("employee", "landlord") when the document states it."""
    first_pages = " ".join(page_text.get(n, "") for n in (1, 2))
    roles = dict(detect_party_roles(first_pages))
    names = list(document.parties) or list(roles)
    return [
        {"entity_id": f"E{i}", "name": name, "role": roles.get(name, "party"), "page_number": 1}
        for i, name in enumerate(names, start=1)
    ]


def _document(document: Document, page_count: int, is_scanned: bool) -> dict[str, Any]:
    return {
        "id": str(document.id),
        "title": Path(document.original_filename).stem.replace("_", " "),
        "original_filename": document.original_filename,
        "format": document.format,
        "mime_type": MIME_TYPES.get(document.format, "application/octet-stream"),
        "language": "en",
        "page_count": max(page_count, 1),
        "is_scanned": is_scanned,
        "classification": classification_for(document),
    }


def _page(number: int, text: str, parsed: Any) -> dict[str, Any]:
    page: dict[str, Any] = {"page_number": number, "text": text, "ocr": {"used": False}}
    if parsed is None:
        return page
    page["width"], page["height"] = parsed.width, parsed.height
    blocks, cursor = [], 0
    for index, block in enumerate(parsed.blocks, start=1):
        entry: dict[str, Any] = {"id": f"P{number}B{index}", "type": block.type, "text": block.text}
        span = _span(text, block.text, cursor)
        if span:
            entry["char_start"], entry["char_end"] = span
            cursor = span[1]
        if block.bbox:
            entry["bbox"] = [round(v, 2) for v in block.bbox]
        blocks.append(entry)
    page["blocks"] = blocks
    return page


def _facts(
    facts: Any, chunks: Any, page_text: dict[int, str], concept_ids: dict[str, str]
) -> tuple[list[dict[str, Any]], dict[uuid.UUID, list[LegalFact]]]:
    chunk_by_id = {c.id: c for c in chunks}
    by_chunk: dict[uuid.UUID, list[LegalFact]] = {}
    result = []
    for fact in facts:
        evidence: dict[str, Any] = {
            "page_number": fact.page_number,
            "source_text": fact.source_text,
        }
        chunk = chunk_by_id.get(fact.chunk_id) if fact.chunk_id else None
        if chunk is not None:
            by_chunk.setdefault(chunk.id, []).append(fact)
            evidence["clause_id"] = str(chunk.id)
            if chunk.heading:
                evidence["section"] = chunk.heading
        if fact.clause_ref:
            evidence["clause_number"] = fact.clause_ref
        span = _span(page_text.get(fact.page_number, ""), fact.source_text)
        if span:
            evidence["char_start"], evidence["char_end"] = span
        entry: dict[str, Any] = {
            "id": str(fact.id),
            "document_id": str(fact.document_id),
            "concept": concept_ids[fact.concept],
            "value": fact.value,
            "evidence": evidence,
            "confidence": fact.confidence
            if fact.confidence is not None
            else FACT_CONFIDENCE.get(fact.concept, KEYWORD_FACT_CONFIDENCE),
            "extraction_method": "rule",
        }
        normalized = fact.normalized_value or normalize(fact.concept, fact.value, fact.source_text)
        if normalized is not None:
            entry["normalized_value"] = normalized
        result.append(entry)
    return result, by_chunk


def _sections(
    chunks: Any, page_text: dict[int, str], facts_by_chunk: dict[uuid.UUID, list[LegalFact]]
) -> list[dict[str, Any]]:
    concept_ids = taxonomy.concept_id_for_engine_key()
    sections: dict[str, dict[str, Any]] = {}
    cursors: dict[int, int] = {}
    for chunk in chunks:
        key = _section_key(chunk.clause_ref, chunk.heading)
        section = sections.get(key)
        if section is None:
            section = {"id": f"S{len(sections) + 1}", "level": 1, "page_start": chunk.page_number,
                       "page_end": chunk.page_number, "clauses": []}  # fmt: skip
            if not key.startswith("heading:"):
                section["number"] = key
            if chunk.heading:
                section["heading"] = chunk.heading
            if role := _role(chunk.heading):
                section["role"] = role
            sections[key] = section
        section["page_end"] = max(section["page_end"], chunk.page_number)

        clause_facts = facts_by_chunk.get(chunk.id, [])
        clause: dict[str, Any] = {
            "id": str(chunk.id),
            "page_number": chunk.page_number,
            "text": chunk.text,
            "concepts": sorted({concept_ids[f.concept] for f in clause_facts}),
            "fact_ids": [str(f.id) for f in clause_facts],
        }
        if chunk.clause_ref:
            clause["clause_number"] = chunk.clause_ref
        text = page_text.get(chunk.page_number, "")
        span = _span(text, chunk.text, cursors.get(chunk.page_number, 0))
        if span:
            clause["char_start"], clause["char_end"] = span
            cursors[chunk.page_number] = span[1]
        section["clauses"].append(clause)
    return list(sections.values())
