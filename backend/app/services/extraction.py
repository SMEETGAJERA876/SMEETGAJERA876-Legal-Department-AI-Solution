"""Fact extraction: finds concept values in sentences, always keeping the exact source text.

Every fact records the sentence it came from (an exact piece of the document), a rule-based
confidence, and — where possible — a normalized value (data/schemas/legal_fact.schema.json).
"""

import re
from dataclasses import dataclass
from typing import Any

from app.services.concepts import CONCEPTS
from app.services.text_utils import normalize_whitespace, split_sentences

_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fourteen": 14, "fifteen": 15,
    "eighteen": 18, "twenty": 20, "twenty-one": 21, "twenty-four": 24, "thirty": 30,
    "thirty-six": 36, "forty-five": 45, "forty five": 45, "sixty": 60, "ninety": 90,
    "one hundred and eighty": 180, "one hundred eighty": 180,
}  # fmt: skip
_NUM = (
    r"(?:\d{1,3}|" + "|".join(sorted(map(re.escape, _NUMBER_WORDS), key=len, reverse=True)) + r")"
)
_UNIT = (
    r"(?:calendar\s+|business\s+|working\s+|clear\s+)?(?P<unit>hours?|days?|weeks?|months?|years?)"
)
_QUANTITY = rf"(?P<word>\b{_NUM})?\s*(?:\((?P<paren>\d{{1,3}})\))?\s*{_UNIT}"
_APOSTROPHE = "(?:['’]s?)?"  # "days' notice", "month's notice"
_MONTHS = (
    r"(?:January|February|March|April|May|June|July|August|September|October|November|"
    r"December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?"
)
_DATE = (
    rf"(?:{_MONTHS}\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}"
    rf"|\d{{1,2}}(?:st|nd|rd|th)?\s+(?:day\s+of\s+)?{_MONTHS},?\s+\d{{4}}"
    r"|\d{4}-\d{2}-\d{2}|\d{1,2}[/.-]\d{1,2}[/.-]\d{4})"
)
_DATE_PATTERN = re.compile(rf"\b{_DATE}\b", re.I)

_NOTICE_PATTERNS = [
    re.compile(
        rf"{_QUANTITY}{_APOSTROPHE}\s*(?:prior\s+|advance\s+)?(?:written\s+)?(?:notice|intimation)",
        re.I,
    ),
    re.compile(
        rf"(?:notice|intimation)\s+(?:period\s+)?of\s+(?:at\s+least\s+|not\s+less\s+than\s+)?"
        rf"{_QUANTITY}",
        re.I,
    ),
]
_TIME_LIMIT_QUANTITY_PATTERNS = [
    (re.compile(rf"\bwithin\s+(?:a\s+period\s+of\s+)?{_QUANTITY}", re.I), "within {q}"),
    (re.compile(rf"\b(?:not|no)\s+later\s+than\s+{_QUANTITY}", re.I), "no later than {q}"),
    (re.compile(rf"{_QUANTITY}\s+(?:from|of)\s+the\s+date\s+of", re.I), "{q} from the date"),
    (re.compile(rf"{_QUANTITY}\s+(?:before|prior\s+to)\b", re.I), "{q} before"),
]
_DEADLINE_DATE_PATTERN = re.compile(
    rf"(?P<lead>on\s+or\s+before|not\s+later\s+than|no\s+later\s+than|by|before|till|until"
    rf"|last\s+date[^.]{{0,40}}?(?:is|:|shall\s+be)|due\s+(?:date|on)[^.]{{0,20}}?)\s*"
    rf"(?P<date>{_DATE})",
    re.I,
)
_DURATION_PATTERNS = [
    re.compile(
        rf"(?:term|period|duration|validity)\s+of\s+(?:this\s+\w+\s+)?(?:shall\s+be\s+)?"
        rf"{_QUANTITY}",
        re.I,
    ),
    re.compile(rf"valid\s+for\s+(?:a\s+period\s+of\s+)?{_QUANTITY}", re.I),
]
_AMOUNT_PATTERN = re.compile(
    r"(?:(?:USD|US\$|INR|EUR|GBP|Rs\.?|₹|\$|€|£)\s?\d[\d,]*(?:\.\d{1,2})?(?:\s?(?:lakhs?|crores?|million))?"
    r"|\b\d[\d,]*(?:\.\d{1,2})?\s?(?:USD|INR|EUR|GBP|dollars|rupees|euros|pounds)\b)",
    re.I,
)
_NOTE_START = re.compile(
    r"^(?:important\s+note|note|n\.\s?b\.?|nb|please\s+note|important|attention|caution|warning)"
    r"\s*[:.\-–—]\s*",
    re.I,
)
_NOTIFIED = re.compile(r"\b(?:it\s+is\s+hereby\s+notified|notice\s+is\s+hereby\s+given)\b", re.I)
_PARTIES_PATTERN = re.compile(
    r"\bbetween\s*:?\s+(?P<a>[A-Z][^,;()]{2,80}?)\s*(?:\([^)]*\))?\s*,?\s*"
    r"and\s+(?P<b>[A-Z][^,;()]{2,80}?)\s*(?:\(|,|\.|;|$)",
)


MAX_FACTS_PER_CONCEPT = 8
KEYWORD_ONLY_CONCEPTS = (
    "termination", "renewal", "penalty", "dispute_resolution", "confidentiality", "liability",
    "obligations", "eligibility", "documents_required", "appeal", "authority", "rights",
    "intellectual_property", "indemnification", "force_majeure", "assignment", "non_compete",
    "non_solicitation",
)  # fmt: skip
EARLY_CHUNKS = 4  # letterhead facts (court, case number, reference) only on the first chunks
MIN_SENTENCE_AFTER_TRIM = 20

# Rule confidences (docs/AI_Pipeline.md §5): explicit wording with a value scores higher than
# a sentence that merely mentions a topic.
CONFIDENCE = {
    "notice_period": 0.9, "time_limits": 0.85, "deadline_date": 0.9, "duration": 0.85,
    "important_dates": 0.9, "payment": 0.8, "specific_money": 0.85, "notes": 0.7,
    "keyword": 0.6, "probation": 0.85, "working_hours": 0.85, "leave": 0.85, "job_title": 0.8,
    "area": 0.85, "interest_rate": 0.85, "governing_law": 0.9, "jurisdiction": 0.85,
    "arbitration": 0.85, "cure_period": 0.85, "reference_number": 0.85, "effective_date": 0.9,
    "contact": 0.9, "court_name": 0.9, "case_number": 0.9,
}  # fmt: skip

# --- leading clutter before the real sentence: "Termination 12.1 ", "(1) ", "TITLE "
_LEADING_CAPS = re.compile(r"^(?:[A-Z][A-Z,'&:-]+\s+)+(?=[A-Z][a-z])")
_LEADING_NUMBER = re.compile(
    r"^(?:\S+\s+){0,6}?(?:\d{1,3}(?:\.\d{1,3})+[.)]?|\(\w{1,4}\))\s+(?=[A-Z(\"“])"
)

# --- money: each amount belongs to the nearest money word
_MONEY_WORDS = [
    ("salary", re.compile(r"\b(?:salary|ctc|wages?|gross pay|basic pay|stipend|remuneration|compensation)\b", re.I)),
    ("rent", re.compile(r"\b(?:rent|licen[cs]e fee)\b", re.I)),
    ("deposit", re.compile(r"\b(?:deposit|security amount|advance)\b", re.I)),
    ("late_fee", re.compile(r"\b(?:late fee|late payment|delayed payment|late charges?)\b", re.I)),
]  # fmt: skip
MONEY_WORD_WINDOW = 80

_PROBATION = re.compile(r"\bprobation", re.I)
_QUANTITY_RE = re.compile(_QUANTITY, re.I)
_HOURS = re.compile(r"\b(?P<n>\d{1,2})\s+hours\s+(?:per|a|each|in\s+a)\s+(?P<per>week|day)\b", re.I)
_TIME = r"\d{1,2}(?:[:.]\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?"
_TIME_RANGE = re.compile(
    rf"\b(?P<a>\d{{1,2}}[:.]\d{{2}}\s*(?:a\.?m\.?|p\.?m\.?)?|\d{{1,2}}\s*(?:a\.?m\.?|p\.?m\.?))\s*(?:to|-|–|until)\s*(?P<b>{_TIME})",
    re.I,
)
_HOURS_CONTEXT = re.compile(r"\b(?:hours|working|office|core|shift|timings?)\b", re.I)
_LEAVE = re.compile(
    rf"{_QUANTITY}\s+(?:of\s+)?(?P<kind>(?:paid|annual|casual|sick|earned|privilege|maternity|paternity)\s+)?leave\b",
    re.I,
)
_JOB_TITLE = re.compile(
    r"\b(?i:appoint(?:s|ed)?\s+(?:you\s+|the\s+employee\s+|him\s+|her\s+)?as|(?:position|post|role)\s+of"
    r"|designation(?:\s+of)?\s*:?)\s+(?i:an?\s+|the\s+)?"
    r"(?P<title>[A-Z][\w&/-]*(?:\s+(?:of\s+|and\s+)?[A-Z][\w&/-]*){0,4})"
)
_AREA = re.compile(
    r"\b(?P<n>\d[\d,]*(?:\.\d+)?)\s*(?P<unit>sq\.?\s*(?:ft|feet|m|metres|meters|yards?|yds?)\b"
    r"|square\s+(?:feet|foot|metres|meters|yards)|acres?|hectares?|cents|guntha)",
    re.I,
)
_INTEREST = re.compile(
    r"(?P<rate>\d{1,2}(?:\.\d{1,2})?)\s*(?:%|per\s*cent|percent)"
    r"(?:\s*(?P<per>p\.?\s*a\.?|per\s+annum|per\s+year|per\s+month|a\s+year|a\s+month))?",
    re.I,
)
_PLACE = r"(?P<place>[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3})"
_GOVERNING_LAW = re.compile(
    rf"governed\s+by\s+(?:and\s+construed\s+in\s+accordance\s+with\s+)?(?:the\s+)?laws?\s+of\s+(?:the\s+)?{_PLACE}"
)
_JURISDICTION = [
    re.compile(rf"courts?\s+(?:at|of|in)\s+{_PLACE}\s+(?:shall|will)\s+have\s+(?:the\s+)?(?:sole\s+and\s+)?(?:exclusive\s+)?jurisdiction"),
    re.compile(rf"jurisdiction\s+of\s+(?:the\s+)?(?:competent\s+)?courts?\s+(?:at|of|in)\s+{_PLACE}"),
]  # fmt: skip
_ARBITRATION = [
    re.compile(rf"arbitration\s+(?:in|at)\s+{_PLACE}"),
    re.compile(rf"(?:seat|venue|place)\s+of\s+(?:the\s+)?arbitration\s+shall\s+be\s+(?:at\s+|in\s+)?{_PLACE}", re.I),
]  # fmt: skip
_CURE = [
    re.compile(rf"(?:cure|remedy|rectify|make\s+good)\s+(?:the\s+|such\s+|any\s+)?(?:breach|default|failure|defect)?\s*(?:with)?in\s+{_QUANTITY}", re.I),
    re.compile(rf"{_QUANTITY}\s+(?:to|in\s+which\s+to)\s+(?:cure|remedy|rectify)", re.I),
]  # fmt: skip
_REFERENCE = re.compile(
    r"\b(?:Ref(?:erence)?\.?(?:\s*No\.?)?|(?:Order|Notification|Circular|File|Policy|Letter|Memo|Notice)\s+No\.?|No\.)"
    r"\s*[:\-]?\s*(?P<ref>[A-Z0-9][A-Za-z0-9]*(?:[/\-.][A-Za-z0-9]+)+)"
)
_EFFECTIVE = [
    re.compile(rf"(?:with\s+effect\s+from|w\.e\.f\.?|effective\s+(?:from|on|as\s+of)|(?:shall\s+)?comes?\s+into\s+(?:force|effect)\s+(?:on|from))\s*[:\-]?\s*(?P<date>{_DATE})", re.I),
    re.compile(rf"effective\s+date[\"”]?\s+(?:means|is|shall\s+be)\s+(?P<date>{_DATE})", re.I),
]  # fmt: skip
_PHONE = re.compile(
    r"(?<!\d)(?:\+91[\s-]?)?(?:1800[\s-]?\d{3}[\s-]?\d{4}|[6-9]\d{4}[\s-]?\d{5}|0\d{2,4}[\s-]\d{6,8})(?!\d)"
)
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
_COURT = [
    re.compile(r"\bIN THE (?P<court>(?:[A-Z']{2,} ){0,3}COURT(?: OF(?: [A-Z]{2,}){1,4})?)"),
    re.compile(r"\b[Ii]n the (?P<court>(?:[A-Z][a-z']+ ){0,3}Court(?: of(?: [A-Z][a-z]+){1,4})?)"),
    re.compile(r"\bBEFORE THE (?P<court>(?:[A-Z']{2,} ){0,4}TRIBUNAL)"),
]  # fmt: skip
_CASE_NUMBER = re.compile(
    r"\b(?:W\.?\s?P\.?|W\.?\s?A\.?|C\.?\s?A\.?|Crl\.?\s?A\.?|O\.?\s?S\.?|C\.?\s?S\.?|S\.?\s?L\.?\s?P\.?"
    r"|Civil\s+Appeal|Criminal\s+Appeal|Writ\s+Petition|Bail\s+Application|Case|Suit|Petition|Appeal)"
    r"\s*(?:\((?:C|Crl|Civil)\)\s*)?No\.?\s*\d{1,6}\s*(?:of|/)\s*\d{4}\b"
)


@dataclass
class ExtractedFact:
    concept: str
    value: str
    source_text: str
    chunk_index: int
    confidence: float
    normalized_value: dict[str, Any] | None = None


def _quantity(match: re.Match[str]) -> str | None:
    number = match.group("paren") or match.group("word")
    if not number:
        return None
    value = int(number) if number.isdigit() else _NUMBER_WORDS.get(number.lower())
    if not value:
        return None
    unit = match.group("unit").lower().rstrip("s")
    return f"{value} {unit}{'' if value == 1 else 's'}"


def _shorten(sentence: str, limit: int = 110) -> str:
    if len(sentence) <= limit:
        return sentence
    return sentence[: limit - 1].rsplit(" ", 1)[0] + "…"


def strip_leading_clutter(sentence: str) -> str:
    """Drop headings and clause numbers before the real sentence. The result is still an exact
    piece of the original text (only a prefix is removed)."""
    for pattern in (_LEADING_CAPS, _LEADING_NUMBER):
        match = pattern.match(sentence)
        if match and len(sentence) - match.end() >= MIN_SENTENCE_AFTER_TRIM:
            sentence = sentence[match.end() :]
    return sentence


class _FactCollector:
    def __init__(self) -> None:
        self.facts: list[ExtractedFact] = []
        self._seen: set[tuple[str, str]] = set()

    def add(
        self, concept: str, value: str, sentence: str, chunk_index: int, rule: str | None = None
    ) -> None:
        key = (concept, value.lower())
        per_concept = sum(1 for f in self.facts if f.concept == concept)
        if key in self._seen or per_concept >= MAX_FACTS_PER_CONCEPT:
            return
        self._seen.add(key)
        from app.services.normalized_values import normalize  # avoid an import cycle

        self.facts.append(
            ExtractedFact(
                concept, value, sentence, chunk_index,
                CONFIDENCE[rule or concept], normalize(concept, value, sentence),
            )
        )  # fmt: skip


def extract_facts(chunks: list[tuple[int, str, str | None]]) -> list[ExtractedFact]:
    """Extract facts from (chunk_index, text, clause heading) tuples."""
    collector = _FactCollector()
    for chunk_index, text, heading in chunks:
        for raw in split_sentences(text):
            sentence = strip_leading_clutter(raw)
            _extract_from_sentence(collector, sentence, chunk_index, heading)
    return collector.facts


def _extract_times(collector: _FactCollector, sentence: str, chunk_index: int) -> None:
    lowered = sentence.lower()
    for pattern in _NOTICE_PATTERNS:
        for match in pattern.finditer(sentence):
            if (quantity := _quantity(match)) is not None:
                collector.add("notice_period", quantity, sentence, chunk_index)
    seen_quantities: set[str] = set()  # "within 15 days from the date of…" counts once
    for pattern, template in _TIME_LIMIT_QUANTITY_PATTERNS:
        for match in pattern.finditer(sentence):
            quantity = _quantity(match)
            if quantity is not None and quantity not in seen_quantities:
                seen_quantities.add(quantity)
                collector.add("time_limits", template.format(q=quantity), sentence, chunk_index)
    for match in _DEADLINE_DATE_PATTERN.finditer(sentence):
        lead = normalize_whitespace(match.group("lead")).lower()
        lead = "last date" if lead.startswith("last date") else lead
        lead = "due" if lead.startswith("due") else lead
        date = normalize_whitespace(match.group("date"))
        collector.add("time_limits", f"{lead} {date}", sentence, chunk_index, "deadline_date")
    if "notice" not in lowered and not _PROBATION.search(sentence):
        for pattern in _DURATION_PATTERNS:
            for match in pattern.finditer(sentence):
                if (quantity := _quantity(match)) is not None:
                    collector.add("duration", quantity, sentence, chunk_index)
    for match in _DATE_PATTERN.finditer(sentence):
        collector.add(
            "important_dates", normalize_whitespace(match.group(0)), sentence, chunk_index
        )


def _money(collector: _FactCollector, sentence: str, chunk_index: int) -> None:
    lowered = sentence.lower()
    money_context = CONCEPTS["payment"].keywords + CONCEPTS["penalty"].keywords
    general = any(kw in lowered for kw in money_context)
    for match in _AMOUNT_PATTERN.finditer(sentence):
        amount = normalize_whitespace(match.group(0))
        owner = _money_owner(sentence, match.start(), match.end())
        if owner:
            collector.add(owner, amount, sentence, chunk_index, "specific_money")
        elif general:
            collector.add("payment", amount, sentence, chunk_index)


def _money_owner(sentence: str, start: int, end: int) -> str | None:
    """The specific money concept whose word is closest before (or just after) the amount."""
    best: tuple[int, str] | None = None
    for concept, pattern in _MONEY_WORDS:
        for word in pattern.finditer(sentence):
            if word.end() <= start and start - word.end() <= MONEY_WORD_WINDOW:
                distance = start - word.end()
            elif word.start() >= end and word.start() - end <= MONEY_WORD_WINDOW // 3:
                distance = word.start() - end + MONEY_WORD_WINDOW  # prefer words before
            else:
                continue
            if best is None or distance < best[0]:
                best = (distance, concept)
    return best[1] if best else None


def _employment(collector: _FactCollector, sentence: str, chunk_index: int) -> None:
    if _PROBATION.search(sentence):
        for match in _QUANTITY_RE.finditer(sentence):
            after = sentence[match.end() : match.end() + 25].lower()
            if "notice" in after or (quantity := _quantity(match)) is None:
                continue  # "fourteen (14) days written notice" is a notice period, not probation
            collector.add("probation", quantity, sentence, chunk_index)
            break
    for match in _HOURS.finditer(sentence):
        collector.add(
            "working_hours",
            f"{match.group('n')} hours per {match.group('per').lower()}",
            sentence,
            chunk_index,
        )
    if _HOURS_CONTEXT.search(sentence):
        for match in _TIME_RANGE.finditer(sentence):
            value = f"{normalize_whitespace(match.group('a'))} to {normalize_whitespace(match.group('b'))}"
            collector.add("working_hours", value, sentence, chunk_index)
    for match in _LEAVE.finditer(sentence):
        if (quantity := _quantity(match)) is not None:
            kind = (match.group("kind") or "").strip().lower()
            collector.add(
                "leave", f"{quantity} of {kind + ' ' if kind else ''}leave", sentence, chunk_index
            )
    for match in _JOB_TITLE.finditer(sentence):
        collector.add("job_title", match.group("title").strip(), sentence, chunk_index)


def _property_and_finance(collector: _FactCollector, sentence: str, chunk_index: int) -> None:
    for match in _AREA.finditer(sentence):
        collector.add(
            "area",
            f"{match.group('n')} {normalize_whitespace(match.group('unit'))}",
            sentence,
            chunk_index,
        )
    if "interest" in sentence.lower():
        for match in _INTEREST.finditer(sentence):
            per = normalize_whitespace(match.group("per") or "")
            collector.add(
                "interest_rate",
                f"{match.group('rate')}%{' ' + per if per else ''}",
                sentence,
                chunk_index,
            )


def _disputes(
    collector: _FactCollector, sentence: str, chunk_index: int, heading: str | None
) -> None:
    if match := _GOVERNING_LAW.search(sentence):
        collector.add("governing_law", f"Laws of {match.group('place')}", sentence, chunk_index)
    for pattern in _JURISDICTION:
        if match := pattern.search(sentence):
            collector.add(
                "jurisdiction", f"Courts at {match.group('place')}", sentence, chunk_index
            )
            break
    seat = next((m for p in _ARBITRATION if (m := p.search(sentence))), None)
    if seat:
        collector.add("arbitration", f"Arbitration in {seat.group('place')}", sentence, chunk_index)
    elif re.search(r"\barbitra", sentence, re.I):
        label = heading if heading and "arbitra" in heading.lower() else _shorten(sentence)
        collector.add("arbitration", label, sentence, chunk_index, "keyword")
    for pattern in _CURE:
        for match in pattern.finditer(sentence):
            if (quantity := _quantity(match)) is not None:
                collector.add("cure_period", quantity, sentence, chunk_index)


def _identity(collector: _FactCollector, sentence: str, chunk_index: int) -> None:
    for pattern in _EFFECTIVE:
        if match := pattern.search(sentence):
            collector.add(
                "effective_date", normalize_whitespace(match.group("date")), sentence, chunk_index
            )
    for match in _PHONE.finditer(sentence):
        collector.add("contact", normalize_whitespace(match.group(0)), sentence, chunk_index)
    for match in _EMAIL.finditer(sentence):
        collector.add("contact", match.group(0), sentence, chunk_index)
    if chunk_index >= EARLY_CHUNKS:
        return
    for match in _REFERENCE.finditer(sentence):
        if any(ch.isdigit() for ch in match.group("ref")):
            collector.add("reference_number", match.group("ref"), sentence, chunk_index)
    for pattern in _COURT:
        if match := pattern.search(sentence):
            collector.add("court_name", _court_name(match.group("court")), sentence, chunk_index)
            break
    for match in _CASE_NUMBER.finditer(sentence):
        collector.add("case_number", normalize_whitespace(match.group(0)), sentence, chunk_index)


def _court_name(text: str) -> str:
    minor = {"of", "the", "at"}
    return " ".join(w.lower() if w.lower() in minor else w.capitalize() for w in text.split())


def _extract_from_sentence(
    collector: _FactCollector, sentence: str, chunk_index: int, heading: str | None
) -> None:
    lowered = sentence.lower()
    _extract_times(collector, sentence, chunk_index)
    _money(collector, sentence, chunk_index)
    _employment(collector, sentence, chunk_index)
    _property_and_finance(collector, sentence, chunk_index)
    _disputes(collector, sentence, chunk_index, heading)
    _identity(collector, sentence, chunk_index)

    note = _NOTE_START.match(sentence)
    heading_is_note = heading is not None and "note" in heading.lower()
    if note or heading_is_note or _NOTIFIED.search(sentence):
        body = sentence[note.end() :] if note else sentence
        collector.add("notes", _shorten(body), sentence, chunk_index)

    for concept in KEYWORD_ONLY_CONCEPTS:
        keywords = CONCEPTS[concept].keywords
        if any(kw in lowered for kw in keywords):
            heading_fits = heading is not None and any(kw in heading.lower() for kw in keywords)
            label = heading if heading_fits and heading else _shorten(sentence)
            collector.add(concept, label, sentence, chunk_index, "keyword")


_ROLE_PATTERN = re.compile(
    r"(?:\bbetween|\band|,)\s*:?\s+(?P<name>[A-Z][\w.&' -]{1,80}?)\s*,?\s*\((?:the\s+|hereinafter\s+"
    r"(?:referred\s+to\s+as\s+|called\s+)?(?:the\s+)?)?[\"“'](?P<role>[A-Z][A-Za-z ]{1,30})[\"”']\)"
)
_NOT_PARTY_ROLES = {
    "agreement",
    "deed",
    "act",
    "rules",
    "scheme",
    "effective date",
    "premises",
    "property",
}


def detect_parties(first_pages_text: str) -> list[str]:
    match = _PARTIES_PATTERN.search(normalize_whitespace(first_pages_text))
    if not match:
        return []
    return [normalize_whitespace(match.group("a")), normalize_whitespace(match.group("b"))]


def detect_party_roles(first_pages_text: str) -> list[tuple[str, str]]:
    """Parties with their role in the document: [("Priya Sharma", "employee"), ...]."""
    text = normalize_whitespace(first_pages_text)
    roles: list[tuple[str, str]] = []
    for match in _ROLE_PATTERN.finditer(text):
        role = match.group("role").strip().lower()
        if role in _NOT_PARTY_ROLES:
            continue
        name = normalize_whitespace(match.group("name"))
        if all(name != existing for existing, _ in roles):
            roles.append((name, re.sub(r"[^a-z]+", "_", role).strip("_")))
    return roles
