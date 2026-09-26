"""Compare an uploaded document against the official format for its kind.

People are handed a rent agreement, an appointment letter or an affidavit and have no way to
tell whether it contains what such a document is supposed to contain. `data/formats/` describes
the expected parts of each kind — what the law or the issuing authority asks for — and this
service reports, part by part:

- **present** — the part was found, with the page it is on;
- **empty** — the part was found but the words around it are an unfilled blank ("Date: ______");
- **missing** — no wording for the part appears anywhere in the document.

Matching is by wording, so it is evidence, not proof: a part can be written in words the format
does not list, and a found phrase can belong to a different sentence. Every finding therefore
carries the page and the exact words, so a person can check it. The website says plainly that
this is a checklist, not a ruling that a document is valid or invalid.
"""

import json
import re
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import DocumentPage
from app.services.text_utils import normalize_whitespace, snippet_around

PartStatus = Literal["present", "empty", "missing"]

# "Date: ______" / "Name .........." — a labelled blank that was never filled in.
_BLANK = re.compile(r"(?:_{3,}|\.{6,}|…{2,})")
# How far after a matched phrase to look for a blank before calling the part empty.
BLANK_WINDOW = 60


@dataclass(frozen=True)
class PartResult:
    id: str
    label: str
    required: bool
    status: PartStatus
    why: str
    page_number: int | None
    evidence: str | None


@dataclass(frozen=True)
class FormatResult:
    format_id: str
    format_name: str
    authority: str
    note: str
    parts: list[PartResult]

    @property
    def missing_required(self) -> list[PartResult]:
        return [p for p in self.parts if p.required and p.status == "missing"]

    @property
    def empty_required(self) -> list[PartResult]:
        return [p for p in self.parts if p.required and p.status == "empty"]

    @property
    def present(self) -> list[PartResult]:
        return [p for p in self.parts if p.status == "present"]

    @property
    def score(self) -> float:
        """Share of required parts that are present. 1.0 means nothing required is missing."""
        required = [p for p in self.parts if p.required]
        if not required:
            return 1.0
        return sum(1 for p in required if p.status == "present") / len(required)


def _formats_dir() -> Path:
    configured = get_settings().formats_dir
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[3] / "data" / "formats"


@lru_cache
def _data() -> dict[str, Any]:
    text = (_formats_dir() / "document_formats.json").read_text(encoding="utf-8")
    data: dict[str, Any] = json.loads(text)
    return data


@lru_cache
def formats() -> tuple[dict[str, Any], ...]:
    return tuple(_data()["formats"])


@lru_cache
def _by_document_type() -> dict[str, dict[str, Any]]:
    return {
        type_id: fmt for fmt in formats() for type_id in fmt["document_type_ids"]
    }


def format_for(document_type_id: str | None) -> dict[str, Any] | None:
    """The official format for this taxonomy type, or None when we don't describe one."""
    if not document_type_id:
        return None
    return _by_document_type().get(document_type_id)


@lru_cache
def _patterns(format_id: str, part_id: str) -> tuple[re.Pattern[str], ...]:
    fmt = next(f for f in formats() if f["id"] == format_id)
    part = next(p for p in fmt["parts"] if p["id"] == part_id)
    compiled = []
    for phrase in part["patterns"]:
        # A phrase like "1." or "to," is punctuation-heavy; match it literally. Word phrases get
        # word boundaries so "act" doesn't match inside "contract".
        escaped = re.escape(phrase)
        boundary = r"\b" if phrase[:1].isalnum() else ""
        trailing = r"\b" if phrase[-1:].isalnum() else ""
        compiled.append(re.compile(boundary + escaped + trailing, re.I))
    return tuple(compiled)


def _pages(db: Session, document_id: uuid.UUID) -> list[tuple[int, str]]:
    rows = db.execute(
        select(DocumentPage.page_number, DocumentPage.text)
        .where(DocumentPage.document_id == document_id)
        .order_by(DocumentPage.page_number)
    ).all()
    return [(number, normalize_whitespace(text or "")) for number, text in rows]


def _find_part(
    pages: list[tuple[int, str]], format_id: str, part: dict[str, Any]
) -> tuple[PartStatus, int | None, str | None]:
    """The first page where this part appears, and whether it looks filled in."""
    first_blank: tuple[int, str] | None = None
    for page_number, text in pages:
        for pattern in _patterns(format_id, part["id"]):
            match = pattern.search(text)
            if match is None:
                continue
            evidence = snippet_around(text, match.start(), match.end())
            following = text[match.end() : match.end() + BLANK_WINDOW]
            if _BLANK.search(following):
                # Remember it, but keep looking: the same part may be filled in elsewhere.
                first_blank = first_blank or (page_number, evidence)
                continue
            return "present", page_number, evidence
    if first_blank is not None:
        return "empty", first_blank[0], first_blank[1]
    return "missing", None, None


def check(
    db: Session, document_id: uuid.UUID, document_type_id: str | None
) -> FormatResult | None:
    """Compare the document against the official format for its kind, or None if we have none."""
    fmt = format_for(document_type_id)
    if fmt is None:
        return None
    pages = _pages(db, document_id)
    parts = []
    for part in fmt["parts"]:
        status, page_number, evidence = _find_part(pages, fmt["id"], part)
        parts.append(
            PartResult(
                id=part["id"],
                label=part["label"],
                required=part["required"],
                status=status,
                why=part["why"],
                page_number=page_number,
                evidence=evidence,
            )
        )
    return FormatResult(
        format_id=fmt["id"],
        format_name=fmt["name"],
        authority=fmt["authority"],
        note=fmt.get("note", ""),
        parts=parts,
    )
