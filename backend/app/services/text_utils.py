import re

_WHITESPACE = re.compile(r"\s+")
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.;!?])\s+(?=[A-Z(\"'“])")


def normalize_whitespace(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip()


# A full stop after these is not the end of a sentence ("No. 12", "Rs. 500", "Pvt. Ltd.").
_ABBREVIATIONS = re.compile(
    r"(?:\b(?:No|Nos|Rs|Mr|Mrs|Ms|Dr|Sr|Jr|St|Ltd|Pvt|Co|Inc|vs|Ref|Hon|Govt|Dept|Art|Sec|Cl"
    r"|approx|etc|viz|i\.e|e\.g)|\b[A-Z](?:\.[A-Z])*)\.$",
    re.IGNORECASE,
)


# "13." on its own is a clause number, not a sentence.
_BARE_NUMBER = re.compile(r"^(?:\d{1,3}(?:\.\d{1,3})*|[IVXLC]{1,6})[.)]$")


def split_sentences(text: str) -> list[str]:
    pieces = [s.strip() for s in _SENTENCE_BOUNDARY.split(normalize_whitespace(text)) if s.strip()]
    sentences: list[str] = []
    for piece in pieces:
        if sentences and (
            _ABBREVIATIONS.search(sentences[-1]) or _BARE_NUMBER.match(sentences[-1])
        ):
            sentences[-1] = f"{sentences[-1]} {piece}"
        else:
            sentences.append(piece)
    return sentences


def compact(text: str) -> str:
    """Lowercase with all whitespace removed — used to match text across PDF extractors."""
    return _WHITESPACE.sub("", text).lower()


def format_clause(ref: str) -> str:
    """'12.1' → 'Clause 12.1'; 'Section 5(1)' and 'Rule 7' are already labelled."""
    return ref if re.match(r"[A-Z][a-z]", ref) else f"Clause {ref}"


def contains_quote(haystack: str, quote: str) -> bool:
    return bool(quote.strip()) and compact(quote) in compact(haystack)


def snippet_around(text: str, start: int, end: int, radius: int = 90) -> str:
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    prefix = "…" if left > 0 else ""
    suffix = "…" if right < len(text) else ""
    return f"{prefix}{text[left:right].strip()}{suffix}"
