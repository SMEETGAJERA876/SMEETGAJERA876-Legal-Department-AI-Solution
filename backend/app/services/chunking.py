"""Split page text into clause-aware chunks while preserving page numbers.

Recognises the numbering styles used by contracts and government documents:
"12. Termination", "12.1 ...", "Clause 4", "Section 5 — Appeals", "Rule 3", "Para 4",
"Article 7", "Chapter II", "IV. Eligibility", sub-sections "(1)", "(a)", "(iv)", and
unnumbered ALL-CAPS headings such as "DOCUMENTS REQUIRED".
"""

import re
from dataclasses import dataclass
from typing import Literal

from app.services.text_utils import normalize_whitespace, split_sentences

MAX_CHUNK_CHARS = 900
MAX_HEADING_CHARS = 70
MAX_CLAUSE_TEXT_CHARS = 3000
MIN_TITLE_CASE_RATIO = 0.6
MIN_CAPS_HEADING_LETTERS = 4

_KEYWORDS = {
    "clause": "",  # "Clause 4" is shown as just "4" (the UI adds "Clause")
    "section": "Section",
    "sec": "Section",
    "article": "Article",
    "art": "Article",
    "rule": "Rule",
    "regulation": "Regulation",
    "para": "Para",
    "paragraph": "Para",
    "chapter": "Chapter",
    "part": "Part",
    "schedule": "Schedule",
    "annexure": "Annexure",
    "appendix": "Appendix",
    "item": "Item",
}
_KEYWORD_HEADING = re.compile(
    r"^(?P<kw>" + "|".join(_KEYWORDS) + r")\.?\s+"
    r"(?P<ref>\d{1,3}[A-Z]?(?:\.\d{1,3})*|[IVXLC]{1,6}|[A-Z])\b[\s.:)\-–—]*(?P<rest>.*)$",
    re.IGNORECASE,
)
# "12. Termination", "12.1 ...", "173.Pawnee's right" (no space), "4A. Inserted section"
_NUMBERED_HEADING = re.compile(
    r"^(?P<ref>\d{1,3}[A-Z]{0,2}(?:\.\d{1,3})*)(?:[.)]\s*|\s+)(?P<rest>[A-Z(\"“].+)$"
)
_ROMAN_HEADING = re.compile(r"^(?P<ref>[IVXLC]{1,5})[.)]\s+(?P<rest>[A-Z].+)$")
_BRACKET_SUBSECTION = re.compile(r"^\((?P<ref>\d{1,2}|[a-z]{1,2}|[ivx]{1,5})\)\s+(?P<rest>\S.*)$")
_PAGE_FOOTER = re.compile(r"^\s*(?:page\s+)?\d+\s*(?:(?:of|/)\s*\d+)?\s*$", re.IGNORECASE)
_MINOR_WORDS = {"a", "an", "and", "as", "at", "by", "for", "in", "of", "on", "or", "the", "to"}
# Words that make a short line a sentence rather than a title.
_VERBS = {
    "shall", "must", "may", "will", "is", "are", "was", "were", "be", "has", "have", "can",
    "should", "means", "includes", "agrees", "pay", "pays", "give", "gives",
}  # fmt: skip
MAX_SENTENCE_CASE_TITLE_WORDS = 8
# Statute style: "12. Constitution of Central Information Commission.—(1) The Central ..."
# (also "22. Powers of Lok Adalat or Permanent Lok Adalat.]—", after an amendment bracket)
# and definition sections: 4. “Promissory note.”—A “Promissory note” is …
_DASH_HEADING = re.compile(
    r"^(?P<title>[A-Z“\"][^—–]{2,250}?)\.[”\"]?\]?\s?(?:—|–|-{1,2})\s*(?P<body>.*)$"
)
MAX_DASH_TITLE_WORDS = 32
# A table of contents ("ARRANGEMENT OF SECTIONS") lists headings; its lines are not clauses.
_CONTENTS_TITLE = re.compile(
    # "arr\w*": official PDFs misspell it too ("ARRENGMENT OF SECTIONS")
    r"^\s*(?:arr\w*\s+of\s+(?:sections|clauses|rules|regulations|paragraphs|articles)"
    r"|table\s+of\s+contents|contents|index)\s*:?\s*$",
    re.IGNORECASE,
)
_BODY_START = re.compile(r"^\s*(?:an\s+act\s+to\b|be\s+it\s+enacted\b|whereas\b)", re.IGNORECASE)
CONTENTS_HEADING = "Contents"
FOOTNOTES_HEADING = "Footnotes"
# Amendment footnotes in consolidated Acts: "1. Subs. by Act 59 of 1994, s. 2 (w.e.f. ...)."
_FOOTNOTE = re.compile(
    r"^\s*\d{1,3}\.\s*(?:subs\.|ins\.|omitted\b|added\b|rep\.|renumbered\b|re-numbered\b"
    r"|the\s+words?\b|certain\s+words\b|vide\b|w\.e\.f\b|see\b|cl\.|clause\s+\(|proviso\b"
    r"|the\s+original\b|now\s+see\b|came\s+into\s+force\b|this\s+act\s+has\s+been\b"
    r"|c\.?\s?f\.|as\s+to\b|for\s+[^.]{1,80}\bsee\b)"
    r"|^\s*\d{1,3}\.\s+.{3,120}\bact,?\s+\d{4}\s*\(\s*\d+\s+of\s+\d{4}\s*\)\.?\s*$",
    re.IGNORECASE,
)
# "2[3. Constitution of ..." — the "2[" opens an amendment; it hides the section number.
# ... and "43. 6[Penalty and compensation] for damage ..." (right after the number)
_AMENDMENT_MARK = re.compile(r"^(\s*)\d{1,2}\[|^(\s*\d{1,3}[A-Z]{0,2}\.\s*)\d{1,2}\[")
_HEADING_MARKS = re.compile(r"\s?\d{1,2}\[|\]")
# Material after the operative text whose numbered lists are not sections of the document.
# A heading on a line of its own ("THE FIRST SCHEDULE", "Schedule [See section 3]"), not a
# sentence that happens to wrap at "the Schedule to the Constitution ...".
_APPENDIX_TITLE = re.compile(
    r"^\s*(?:THE\s+)?(?:(?:FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH)\s+)?"
    r"SCHEDULE\s*[.:]?\s*(?:[\[(]\s*[Ss]ee\b.*)?$"
    r"|^\s*STATEMENT\s+OF\s+OBJECTS\s+AND\s+REASONS\s*[.:]?\s*$"
)  # capitals: "…in the third column of the\nSchedule." is a wrapped sentence, not a heading
# "…the Constitution.   6. Consent.––(1) The consent…": a section that starts mid-line.
_INLINE_SECTION = re.compile(
    r"(?<=[.;:])\s{2,}(?=\d{1,3}[A-Z]{0,2}\.\s+[A-Z][^.\n]{2,150}\.\]?\s?(?:—|–|-{1,2}))"
)
MAX_CONTENTS_PAGES = 10
MIN_CONTENTS_ENTRIES = 3


def is_footnote(line: str) -> bool:
    return bool(_FOOTNOTE.match(line))


StartKind = Literal["top", "dotted", "bracket"]


@dataclass(frozen=True)
class ClauseStart:
    ref: str
    heading: str | None
    kind: StartKind
    has_body: bool = False  # the line continues with clause text, not just a title

    @property
    def is_top_level(self) -> bool:
        return self.kind == "top"


@dataclass
class Chunk:
    page_number: int
    chunk_index: int
    text: str
    clause_ref: str | None
    heading: str | None


@dataclass
class ClauseRecord:
    page_number: int
    clause_ref: str
    heading: str | None
    text: str


def _looks_like_title(text: str) -> bool:
    """'Termination', 'Governing Law and Disputes' → True; ordinary sentences → False."""
    if not text or len(text) > MAX_HEADING_CHARS or text.endswith((".", ";", ",")):
        return False
    if text.isupper():
        return True
    found: list[str] = re.findall(r"[A-Za-z][\w'-]*", text)
    words = [w for w in found if w.lower() not in _MINOR_WORDS]
    if not words:
        return False
    if sum(w[0].isupper() for w in words) / len(words) >= MIN_TITLE_CASE_RATIO:
        return True
    # Sentence-case titles: "Short title and commencement", "Last date for applying"
    return (
        found[0][0].isupper()
        and len(found) <= MAX_SENTENCE_CASE_TITLE_WORDS
        and not any(w.lower() in _VERBS for w in found)
    )


def is_caps_heading(line: str) -> bool:
    """Unnumbered headings such as 'DOCUMENTS REQUIRED' or 'IMPORTANT NOTE:'."""
    stripped = line.strip().rstrip(":")
    letters = sum(ch.isalpha() for ch in stripped)
    return (
        letters >= MIN_CAPS_HEADING_LETTERS
        and len(stripped) <= MAX_HEADING_CHARS
        and stripped.isupper()
        and not stripped.endswith((".", ";", ","))
    )


def _number_key(ref: str) -> str:
    """'Section 5.2(1)' → '5'; '12.1' → '12'; 'Chapter II' → 'II'."""
    return re.split(r"[.(]", ref.split()[-1], maxsplit=1)[0]


def detect_clause_start(line: str) -> ClauseStart | None:
    stripped = line.strip()
    if (match := _KEYWORD_HEADING.match(stripped)) and stripped[0].isupper():
        prefix = _KEYWORDS[match.group("kw").lower()]
        number = match.group("ref")
        ref = f"{prefix} {number}" if prefix else number
        kind: StartKind = "dotted" if "." in number and not prefix else "top"
    elif match := _NUMBERED_HEADING.match(stripped):
        ref = match.group("ref")
        kind = "dotted" if "." in ref else "top"
    elif match := _ROMAN_HEADING.match(stripped):
        ref, kind = match.group("ref"), "top"
    elif match := _BRACKET_SUBSECTION.match(stripped):
        ref, kind = f"({match.group('ref')})", "bracket"
    else:
        return None
    rest = match.group("rest").strip().rstrip(":")
    if kind == "top" and (dash := _DASH_HEADING.match(rest)):
        title = _HEADING_MARKS.sub(" ", dash.group("title")).replace("“", "").replace("”", "")
        title = title.strip().strip('"')
        title = normalize_whitespace(title)
        if len(title.split()) <= MAX_DASH_TITLE_WORDS:
            return ClauseStart(ref=ref, heading=title, kind=kind, has_body=True)
    heading = rest if kind == "top" and _looks_like_title(rest) else None
    return ClauseStart(ref=ref, heading=heading, kind=kind, has_body=bool(rest) and not heading)


def starts_statute_section(line: str) -> bool:
    """'5. Designation of Public Information Officers.—(1) Every ...'"""
    start = detect_clause_start(line)
    return bool(start and start.is_top_level and start.has_body and start.heading)


def _split_long(text: str) -> list[str]:
    if len(text) <= MAX_CHUNK_CHARS:
        return [text]
    pieces: list[str] = []
    current = ""
    for sentence in split_sentences(text):
        if current and len(current) + len(sentence) + 1 > MAX_CHUNK_CHARS:
            pieces.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        pieces.append(current)
    return pieces


def _bracket_style(ref: str) -> str:
    inner = ref.strip("()")
    if inner.isdigit():
        return "digit"
    return "roman" if set(inner) <= set("ivx") and len(inner) > 1 else "alpha"


class _Chunker:
    def __init__(self) -> None:
        self.chunks: list[Chunk] = []
        self.clauses: list[ClauseRecord] = []
        self.top_ref: str | None = None
        self.clause_ref: str | None = None
        self.heading: str | None = None
        self.lines: list[str] = []
        self.only_heading_lines = False  # pending lines are just a heading like "12. Termination"
        self.awaiting_title = False  # "CHAPTER II" whose title is on the next line
        self.in_contents = False  # inside a table of contents
        self.contents_page: int | None = None
        self.contents_numbers: list[str] = []
        self.footnotes: list[str] = []
        self.in_footnote = False
        self.appendix: str | None = None  # inside a Schedule / Statement of Objects and Reasons

    def flush_footnotes(self, page_number: int) -> None:
        """Footnotes become their own chunk; the clause in progress carries on after them."""
        text = normalize_whitespace(" ".join(self.footnotes))
        self.footnotes.clear()
        self.in_footnote = False
        for piece in _split_long(text) if text else []:
            self.chunks.append(Chunk(page_number, len(self.chunks), piece, None, FOOTNOTES_HEADING))

    def flush(self, page_number: int) -> None:
        text = normalize_whitespace(" ".join(self.lines))
        self.lines.clear()
        self.only_heading_lines = False
        if not text:
            return
        for piece in _split_long(text):
            self.chunks.append(
                Chunk(page_number, len(self.chunks), piece, self.clause_ref, self.heading)
            )
        if self.clauses and self.top_ref == self.clauses[-1].clause_ref:
            record = self.clauses[-1]
            if len(record.text) < MAX_CLAUSE_TEXT_CHARS:
                combined = normalize_whitespace(f"{record.text} {text}")
                record.text = combined[:MAX_CLAUSE_TEXT_CHARS]

    def _sub_ref(self, start: ClauseStart) -> str:
        if start.kind == "dotted":
            if self.top_ref and _number_key(self.top_ref) == _number_key(start.ref):
                prefix = self.top_ref.rsplit(" ", 1)[0] if " " in self.top_ref else ""
                return f"{prefix} {start.ref}".strip()
            return start.ref
        base = self.clause_ref or self.top_ref or ""
        # "(2)" after "5(1)(b)" replaces "(1)(b)": cut back to the same bracket style.
        brackets = list(re.finditer(r"\([^()]*\)", base))
        for bracket in reversed(brackets):
            if _bracket_style(bracket.group(0)) == _bracket_style(start.ref):
                base = base[: bracket.start()]
                break
        return f"{base}{start.ref}"

    def start_clause(self, page_number: int, start: ClauseStart) -> None:
        keeps_heading = (
            self.only_heading_lines
            and not start.is_top_level
            and (
                start.kind == "bracket" or _number_key(start.ref) == _number_key(self.top_ref or "")
            )
        )
        if not keeps_heading:  # keep "12. Termination" together with "12.1 ..."
            self.flush(page_number)
        self.awaiting_title = False
        if start.is_top_level:
            self.top_ref = self.clause_ref = start.ref
            self.heading = start.heading
            self.awaiting_title = start.heading is None
            self.clauses.append(ClauseRecord(page_number, start.ref, start.heading, ""))
            self.only_heading_lines = not start.has_body
            return
        if start.kind == "dotted" and (
            self.top_ref is None or _number_key(self.top_ref) != _number_key(start.ref)
        ):
            self.heading = None  # sub-clause of a clause we never saw a heading for
            self.top_ref = start.ref.split(".", 1)[0]
        self.clause_ref = self._sub_ref(start)
        self.only_heading_lines = False

    def _plausible_bracket(self, ref: str) -> bool:
        """'(2)' must follow '(1)', '(b)' must follow '(a)'. Rejects wrapped lines like
        '(30) days of the order.' that only look like sub-sections."""
        inner = ref.strip("()")
        if inner in ("1", "a", "i"):
            return True
        previous = re.findall(r"\(([^()]*)\)", self.clause_ref or "")
        same_style = [p for p in previous if _bracket_style(f"({p})") == _bracket_style(ref)]
        if not same_style:
            return False
        last = same_style[-1]
        if inner.isdigit() and last.isdigit():
            return int(inner) == int(last) + 1
        if len(inner) == 1 and len(last) == 1:
            return ord(inner) == ord(last) + 1
        return _bracket_style(ref) == "roman"

    def _contents_line(self, page_number: int, line: str) -> bool:
        """Handle a line inside a table of contents. False = the contents have ended."""
        start = detect_clause_start(line)
        number = _number_key(start.ref) if start and start.is_top_level else None
        restarts = (
            number is not None
            and len(self.contents_numbers) >= MIN_CONTENTS_ENTRIES
            and number == self.contents_numbers[0]
            and not (number.isupper() and number.isalpha())  # "CHAPTER I" repeats in contents
        )
        too_long = page_number - (self.contents_page or page_number) >= MAX_CONTENTS_PAGES
        if restarts or too_long or _BODY_START.match(line) or starts_statute_section(line):
            self.flush(page_number)
            self.in_contents = False
            self.heading = None
            return False
        if number and number.isdigit():
            self.contents_numbers.append(number)
        self.lines.append(line)
        return True

    def add_line(self, page_number: int, line: str) -> None:
        line = _AMENDMENT_MARK.sub(lambda m: m.group(1) or m.group(2) or "", line)
        # A footnote may wrap onto following lines; a blank line or a new clause ends it.
        if is_footnote(line) or (
            self.in_footnote and line.strip() and not detect_clause_start(line)
        ):
            self.footnotes.append(line)
            self.in_footnote = True
            return
        self.in_footnote = False
        if self.in_contents and self._contents_line(page_number, line):
            return
        if not self.in_contents and self.clauses and _APPENDIX_TITLE.match(line):
            self.flush(page_number)
            self.appendix = normalize_whitespace(line).strip(" .:").title()
            self.top_ref = self.clause_ref = None
            self.heading = self.appendix
            self.lines.append(line)
            return
        if self.appendix:  # its numbered items are list entries, not sections
            self.lines.append(line)
            return
        if _CONTENTS_TITLE.match(line) and not self.contents_numbers:
            self.flush(page_number)
            self.in_contents = True
            self.contents_page = page_number
            self.top_ref = self.clause_ref = None
            self.heading = CONTENTS_HEADING
            self.lines.append(line)
            return
        start = detect_clause_start(line)
        if start and start.kind == "bracket" and not self._plausible_bracket(start.ref):
            start = None
        if start:
            self.start_clause(page_number, start)
            self.lines.append(line)
            return
        if self.awaiting_title and line.strip() and _looks_like_title(line.strip()):
            title = line.strip().rstrip(":")
            self.heading = title
            if self.clauses and self.clauses[-1].clause_ref == self.top_ref:
                self.clauses[-1].heading = title
            self.awaiting_title = False
            self.lines.append(line)
            return
        if line.strip():
            self.awaiting_title = False
        if is_caps_heading(line) and not self.only_heading_lines:
            self.flush(page_number)
            self.heading = line.strip().rstrip(":")
            self.only_heading_lines = True
            self.lines.append(line)
            return
        if line.strip():
            self.only_heading_lines = False
        self.lines.append(line)


def chunk_pages(pages: list[str]) -> tuple[list[Chunk], list[ClauseRecord]]:
    """Chunk every page. The active clause carries over from one page to the next.

    Top-level clauses (e.g. "12. Termination", "Section 5") become clause records;
    sub-clauses ("12.1", "(a)") keep their own reference and inherit the parent's heading.
    """
    chunker = _Chunker()
    for page_number, page_text in enumerate(pages, start=1):
        for line in _INLINE_SECTION.sub("\n", page_text).splitlines():
            if not _PAGE_FOOTER.match(line):
                chunker.add_line(page_number, line)
        chunker.flush(page_number)
        chunker.flush_footnotes(page_number)
    return chunker.chunks, [c for c in chunker.clauses if c.text]
