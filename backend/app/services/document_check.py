"""Find likely mistakes in a document, each with its page, the exact words and a suggestion.

Two kinds of findings:
- "fix": mechanical mistakes that can be repaired automatically (spelling, repeated words).
- "review": problems where only a person can decide what is right (numbers in words and
  digits that disagree, references to clauses that don't exist, missing clause numbers,
  unclosed brackets, blanks that were never filled in). These are never changed
  automatically, because changing them could change the meaning of the document.
"""

import hashlib
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from spellchecker import SpellChecker

from app.services.text_utils import normalize_whitespace, snippet_around, split_sentences

IssueKind = Literal[
    "spelling",
    "repeated_word",
    "number_mismatch",
    "missing_reference",
    "numbering_gap",
    "duplicate_number",
    "unclosed_bracket",
    "blank_field",
]
FIXABLE_KINDS: set[str] = {"spelling", "repeated_word"}
KIND_LABELS: dict[str, str] = {
    "spelling": "Possible spelling mistake",
    "repeated_word": "Word repeated twice",
    "number_mismatch": "Number in words and digits don't match",
    "missing_reference": "Refers to a clause that doesn't exist",
    "numbering_gap": "Clause number missing",
    "duplicate_number": "Clause number used twice",
    "unclosed_bracket": "Bracket opened but not closed",
    "blank_field": "Blank not filled in",
}

MIN_SPELLCHECK_LENGTH = 4
MAX_SPELLING_DISTANCE = 2
MAX_ISSUES = 200

# Legal and government words a general dictionary may not know.
LEGAL_WORDS = [
    "hereinafter", "hereunder", "hereto", "herein", "hereby", "thereof", "therein", "thereto",
    "whereof", "whereas", "notwithstanding", "indemnify", "indemnified", "indemnity", "lessee",
    "lessor", "licensee", "licensor", "arbitral", "appellate", "aggrieved", "affidavit",
    "attested", "deponent", "undersigned", "vendee", "vendor", "mortgagor", "mortgagee",
    "assignee", "assignor", "payee", "encumbrance", "encumbrances", "severability", "sublet",
    "subletting", "sublease", "gazette", "tribunal", "adjudicating", "adjudication",
    "cognizable", "stamp", "notarised", "notarized", "licence", "licences", "organisation",
    "authorised", "authorized", "utilise", "judgement", "cheque", "cheques", "rupees", "lakh",
    "lakhs", "crore", "crores", "taluk", "tehsil", "panchayat", "municipal", "aadhaar", "gst",
    "pan", "rti", "annexure", "annexures", "addendum", "sanctioned", "remuneration",
]  # fmt: skip

_WORD = re.compile(r"(?<![\w-])([a-z][a-z']{3,})(?![\w-])")
_HYPHEN_BREAK = re.compile(r"(\w+)-\n(\w+)")
_REPEATED = re.compile(r"\b([A-Za-z]+)([ \t]+)\1\b", re.IGNORECASE)
_BLANK = re.compile(
    r"_{3,}|\.{6,}|\[(?:insert|date|name|amount|address|place|details?)[^\]]{0,40}\]"
    r"|\bX{3,}\b",
    re.IGNORECASE,
)
_REFERENCE = re.compile(
    r"\b(?P<kw>Clause|Section|Rule|Article|Para(?:graph)?)\s+(?P<num>\d{1,3})(?![\d(]|\.\d)"
    r"(?P<after>\s+of\s+(?:the\s+)?[A-Z])?"
)
_REPEAT_ALLOWED = {"that", "had", "is", "do"}  # "that that", "had had" can be correct

_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19,
}  # fmt: skip
_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90,
}  # fmt: skip
_NUMBER_WORD = (
    r"(?:" + "|".join(sorted([*_UNITS, *_TENS, "hundred", "and"], key=len, reverse=True)) + r")"
)
_WORDS_THEN_DIGITS = re.compile(
    rf"\b(?P<words>{_NUMBER_WORD}(?:[\s-]+{_NUMBER_WORD})*)\s*\((?P<digits>\d{{1,4}})\)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Issue:
    id: str
    kind: str
    page_number: int
    original: str  # the exact words on the page
    suggestion: str | None  # replacement text for fixable issues
    message: str
    context: str
    occurrence: int = 0  # which occurrence of `original` on the page (0 = first)

    @property
    def fixable(self) -> bool:
        return self.kind in FIXABLE_KINDS and self.suggestion is not None

    @property
    def label(self) -> str:
        return KIND_LABELS[self.kind]


@dataclass(frozen=True)
class ClauseInfo:
    page_number: int
    clause_ref: str


@lru_cache
def _speller() -> SpellChecker:
    speller = SpellChecker(distance=MAX_SPELLING_DISTANCE)
    speller.word_frequency.load_words(LEGAL_WORDS)
    return speller


def words_to_number(text: str) -> int | None:
    """'ninety' → 90, 'forty-five' → 45, 'one hundred and twenty' → 120."""
    total = 0
    current = 0
    for word in re.split(r"[\s-]+", text.lower()):
        if word == "and" or not word:
            continue
        if word in _UNITS:
            current += _UNITS[word]
        elif word in _TENS:
            current += _TENS[word]
        elif word == "hundred":
            current = max(current, 1) * 100
        else:
            return None
    return total + current


class _Collector:
    def __init__(self) -> None:
        self.issues: list[Issue] = []
        self._occurrences: Counter[tuple[str, int, str]] = Counter()

    def add(
        self,
        kind: IssueKind,
        page_number: int,
        original: str,
        message: str,
        page_text: str,
        start: int,
        suggestion: str | None = None,
    ) -> None:
        key = (kind, page_number, original)
        occurrence = self._occurrences[key]
        self._occurrences[key] += 1
        digest = hashlib.sha1(f"{kind}|{page_number}|{original}|{occurrence}".encode())
        context = normalize_whitespace(snippet_around(page_text, start, start + len(original), 60))
        self.issues.append(
            Issue(
                digest.hexdigest()[:12],
                kind,
                page_number,
                original,
                suggestion,
                message,
                context,
                occurrence,
            )  # fmt: skip
        )


def _match_case(template: str, word: str) -> str:
    if template.isupper():
        return word.upper()
    if template[:1].isupper():
        return word[:1].upper() + word[1:]
    return word


_PREFIXES = ("un", "non", "re", "pre", "mis", "sub", "over", "under", "dis", "co", "inter")
_SUFFIXES = ("ed", "ing", "s", "es", "ly", "ment", "ness", "able")


def _is_derived_word(word: str, speller: SpellChecker) -> bool:
    """'unserved', 'reallocate', 'nonpayment' are real words built from known ones."""
    for prefix in _PREFIXES:
        rest = word[len(prefix) :]
        if word.startswith(prefix) and len(rest) >= MIN_SPELLCHECK_LENGTH:
            if not speller.unknown([rest]) or _is_derived_word(rest, speller):
                return True
    for suffix in _SUFFIXES:
        stem = word[: -len(suffix)]
        if word.endswith(suffix) and len(stem) >= MIN_SPELLCHECK_LENGTH:
            restored_e = stem + "e" if suffix in ("ed", "ing", "able") else stem  # "served"
            if not speller.unknown([stem]) or not speller.unknown([restored_e]):
                return True
    return False


def _check_spelling(collector: _Collector, pages: list[str]) -> None:
    speller = _speller()
    counts: Counter[str] = Counter(
        w for text in pages for w in _WORD.findall(_HYPHEN_BREAK.sub(r"\1\2", text).lower())
    )
    for page_number, text in enumerate(pages, start=1):
        broken = {m.group(1).lower() for m in _HYPHEN_BREAK.finditer(text)} | {
            m.group(2).lower() for m in _HYPHEN_BREAK.finditer(text)
        }
        for match in _WORD.finditer(text):
            word = match.group(1).strip("'")
            if (
                len(word) < MIN_SPELLCHECK_LENGTH
                or word in broken
                or counts[word] > 1  # used more than once: probably intentional
                or not speller.unknown([word])
            ):
                continue
            if _is_derived_word(word, speller):
                continue
            suggestion = speller.correction(word)
            if not suggestion or suggestion == word:
                continue
            collector.add(
                "spelling", page_number, word,
                f"“{word}” may be misspelled. Did you mean “{suggestion}”?",
                text, match.start(), _match_case(word, suggestion),
            )  # fmt: skip


def _check_repeated_words(collector: _Collector, pages: list[str]) -> None:
    for page_number, text in enumerate(pages, start=1):
        for match in _REPEATED.finditer(text):
            word = match.group(1)
            if word.lower() in _REPEAT_ALLOWED or word.isdigit():
                continue
            collector.add(
                "repeated_word", page_number, match.group(0),
                f"“{word}” appears twice in a row.", text, match.start(), word,
            )  # fmt: skip


def _check_numbers(collector: _Collector, pages: list[str]) -> None:
    for page_number, text in enumerate(pages, start=1):
        for match in _WORDS_THEN_DIGITS.finditer(text):
            words = normalize_whitespace(match.group("words"))
            value = words_to_number(words)
            digits = int(match.group("digits"))
            if value is None or value == 0 or value == digits:
                continue
            collector.add(
                "number_mismatch", page_number, normalize_whitespace(match.group(0)),
                f"“{words}” means {value}, but the digits say {digits}. Check which number is "
                "intended — this can change what the document means.",
                text, match.start(),
            )  # fmt: skip


def _check_blanks(collector: _Collector, pages: list[str]) -> None:
    for page_number, text in enumerate(pages, start=1):
        for match in _BLANK.finditer(text):
            collector.add(
                "blank_field", page_number, match.group(0),
                "This looks like a blank that was never filled in.", text, match.start(),
            )  # fmt: skip


def _check_brackets(collector: _Collector, pages: list[str]) -> None:
    for page_number, raw in enumerate(pages, start=1):
        text = normalize_whitespace(raw)
        position = 0
        for sentence in split_sentences(text):
            position = text.find(sentence, position)
            depth, opened_at = 0, -1
            for index, char in enumerate(sentence):
                if char == "(":
                    depth, opened_at = depth + 1, index
                elif char == ")":
                    depth = max(0, depth - 1)
            if depth > 0 and opened_at >= 0:
                original = " ".join(sentence[opened_at:].split()[:3])
                collector.add(
                    "unclosed_bracket", page_number, original,
                    "A bracket “(” is opened here but never closed — part of the sentence may "
                    "be missing.", text, position + opened_at,
                )  # fmt: skip
            position += len(sentence)


def _plain_number(ref: str) -> int | None:
    return int(ref) if ref.isdigit() else None


def _check_structure(collector: _Collector, pages: list[str], clauses: list[ClauseInfo]) -> None:
    numbered = sorted(
        ((c, n) for c in clauses if (n := _plain_number(c.clause_ref)) is not None),
        key=lambda pair: (pair[0].page_number, pair[1]),  # stored clauses have no order
    )
    seen: dict[int, ClauseInfo] = {}
    previous: int | None = None
    for clause, number in numbered:
        page_text = pages[clause.page_number - 1]
        position = max(page_text.find(f"{number}."), 0)
        if number in seen:
            collector.add(
                "duplicate_number", clause.page_number, f"{number}.",
                f"Clause {number} appears twice (also on page {seen[number].page_number}).",
                page_text, position,
            )  # fmt: skip
        elif previous is not None and number > previous + 1:
            missing = ", ".join(str(n) for n in range(previous + 1, number))
            collector.add(
                "numbering_gap", clause.page_number, f"{number}.",
                f"Clause numbering jumps from {previous} to {number} — clause {missing} "
                "seems to be missing.", page_text, position,
            )  # fmt: skip
        seen.setdefault(number, clause)
        previous = number

    known = {c.clause_ref.lower() for c in clauses} | {
        f"clause {n}" for n in seen
    }  # "Clause 4" and plain "4." both count
    has_type = {c.clause_ref.split()[0].lower() for c in clauses if " " in c.clause_ref}
    if seen:
        has_type.add("clause")
    for page_number, text in enumerate(pages, start=1):
        for match in _REFERENCE.finditer(text):
            if match.group("after"):  # "Section 138 of the Negotiable Instruments Act"
                continue
            keyword = (
                "para"
                if match.group("kw").lower().startswith("para")
                else match.group("kw").lower()
            )
            reference = f"{keyword} {match.group('num')}"
            if keyword not in has_type or reference in known:
                continue
            collector.add(
                "missing_reference", page_number, normalize_whitespace(match.group(0)),
                f"The document refers to {match.group('kw')} {match.group('num')}, but no such "
                f"{match.group('kw').lower()} was found. The reference may be wrong.",
                text, match.start(),
            )  # fmt: skip


def check_document(pages: list[str], clauses: list[ClauseInfo]) -> list[Issue]:
    collector = _Collector()
    _check_spelling(collector, pages)
    _check_repeated_words(collector, pages)
    _check_numbers(collector, pages)
    _check_structure(collector, pages, clauses)
    _check_brackets(collector, pages)
    _check_blanks(collector, pages)
    issues = sorted(collector.issues, key=lambda i: (i.page_number, not i.fixable))
    return issues[:MAX_ISSUES]
