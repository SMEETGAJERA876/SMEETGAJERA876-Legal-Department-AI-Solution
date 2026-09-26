"""Turn formal legal and government wording into everyday words.

This runs locally with no API key: it is a dictionary of legal → plain wording
(`data/taxonomy/legal_to_plain.json`) plus a few safe structural changes. That is a deliberate
limit. A rewriter that *understands* a clause could also misunderstand it, so this one only ever
does things that cannot change the meaning:

- replace a formal word or phrase with an everyday one ("lessee" → "tenant");
- write numbers written as words as digits too ("forty-five days" → "45 days");
- split a very long sentence at a semicolon;
- shorten the citation clutter that surrounds statutory text.

It never drops a number, a date, an amount, a party, a condition or a negation, never reorders
clauses, and never adds a fact. The simplified text is always shown **beside** the original
wording, never instead of it — `simplified()` returns both, and the website labels which is which.

When an AI provider is configured it writes a better explanation (services/ai_provider.py); this
is the baseline that is always available, including on a deployment with no key at all.
"""

import re
from dataclasses import dataclass
from functools import lru_cache

from app.services import taxonomy
from app.services.document_check import words_to_number
from app.services.text_utils import normalize_whitespace, split_sentences

# Long enough that splitting helps, short enough that we don't chop ordinary sentences.
LONG_SENTENCE_WORDS = 34
# A piece of a split sentence shorter than this is a fragment, not a sentence.
MIN_SPLIT_WORDS = 5
MAX_SIMPLIFIED_SENTENCES = 6

# "(2) " / "12. " / "(a) " at the start of statutory text: useful in the original, noise in a
# plain-language version that already says where it came from.
_LEADING_ENUMERATOR = re.compile(r"^\s*(?:\(?\d{1,3}[.)]|\([a-z]\)|\([ivx]{1,5}\))\s*")
# "—" after a heading in India Code text: "41. Appeal against order.—Any person…"
_HEADING_DASH = re.compile(r"^(.{0,80}?)\.\s*[—–-]\s*")
# Number words, possibly hyphenated: "forty-five", "ninety", "one hundred and twenty".
_NUMBER_WORDS = re.compile(
    r"\b(?:(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen"
    r"|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy"
    r"|eighty|ninety|hundred|thousand)(?:[-\s]+(?:and[-\s]+)?)?)+\b",
    re.I,
)
# A number word immediately followed by the same value in digits — "ninety (90) days". Already
# unambiguous, so leave it alone rather than producing "90 (90) days".
_ALREADY_IN_DIGITS = re.compile(r"^\s*\(\s*\d")
_TRAILING_SEPARATOR = re.compile(r"[-\s]+$")
# Substituting a phrase that already followed an article can double it ("the the property").
_DOUBLED_ARTICLE = re.compile(r"(the|a|an)\s+(the|a|an)", re.I)


@dataclass(frozen=True)
class Simplified:
    """The original wording and the plain-language version of it, always together."""

    original: str
    simple: str
    #: The formal terms that were replaced, as (legal, plain) — shown as "what these words mean".
    terms: list[tuple[str, str]]
    #: True when a number written in words was also written in digits.
    numbers_rewritten: bool = False

    @property
    def changed(self) -> bool:
        return self.simple.strip().casefold() != self.original.strip().casefold()

    @property
    def worth_showing(self) -> bool:
        """Whether the plain version earns its place beside the original.

        Stripping "(b) " and splitting a sentence are tidying, not translation. Only a passage
        where formal wording or a number in words was actually replaced is worth showing twice.
        """
        return bool(self.terms) or self.numbers_rewritten


@lru_cache
def _rules() -> tuple[tuple[re.Pattern[str], str, str], ...]:
    """(pattern, plain wording, the legal term it stands for), longest legal phrase first."""
    data = taxonomy.load("legal_to_plain.json")
    pairs: list[tuple[str, str]] = []
    for rule in data["rewrites"]:
        for legal in rule["legal"]:
            pairs.append((legal, rule["plain"]))
    pairs.sort(key=lambda pair: len(pair[0]), reverse=True)
    return tuple(
        (re.compile(rf"\b{re.escape(legal)}\b", re.I), plain, legal)
        for legal, plain in pairs
        # A rule that maps a word to itself is there to protect it from a broader rule.
        if legal.casefold() != plain.casefold()
    )


def _match_case(original: str, replacement: str) -> str:
    """Keep the shape of the original word so sentences still read correctly."""
    if original.isupper() and len(original) > 1:
        return replacement.upper()
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def _numbers_as_digits(text: str) -> tuple[str, bool]:
    """"forty-five days" → "45 days". Never touches a number that is already in digits."""

    def replace(match: re.Match[str]) -> str:
        words = match.group(0)
        if _ALREADY_IN_DIGITS.match(text[match.end() :]):
            return words
        # The pattern may swallow the separator after the last word ("forty-five " ); keep it,
        # or the digits run into the next word ("45days").
        trailing = _TRAILING_SEPARATOR.search(words)
        separator = trailing.group(0) if trailing else ""
        value = words_to_number(words[: trailing.start()] if trailing else words)
        # Single small words ("one of the parties") read worse as digits than as words.
        if value is None or value < 10:
            return words
        rewritten.append(True)
        return f"{value}{separator}"

    rewritten: list[bool] = []
    return _NUMBER_WORDS.sub(replace, text), bool(rewritten)


def _apply_terms(text: str) -> tuple[str, list[tuple[str, str]]]:
    used: list[tuple[str, str]] = []
    # Placeholders stop an already-substituted phrase from being rewritten again by a later rule.
    replacements: list[str] = []

    def store(value: str) -> str:
        replacements.append(value)
        return f"\x00{len(replacements) - 1}\x00"

    for pattern, plain, legal in _rules():
        if not pattern.search(text):
            continue

        def replace(match: re.Match[str], plain: str = plain) -> str:
            return store(_match_case(match.group(0), plain))

        text = pattern.sub(replace, text)
        if (legal, plain) not in used:
            used.append((legal, plain))
    for index, value in enumerate(replacements):
        text = text.replace(f"\x00{index}\x00", value)
    return text, used


def _split_long_sentence(sentence: str) -> list[str]:
    if len(sentence.split()) <= LONG_SENTENCE_WORDS or ";" not in sentence:
        return [sentence]
    parts = [part.strip(" ;") for part in sentence.split(";")]
    parts = [part for part in parts if part]
    # "…in design; or" would leave "or" as its own sentence: keep the original instead.
    if len(parts) < 2 or any(len(part.split()) < MIN_SPLIT_WORDS for part in parts):
        return [sentence]
    return [part if part.endswith(".") else part + "." for part in parts]


def simplified(text: str) -> Simplified:
    """The plain-language version of a passage, beside the original wording."""
    original = normalize_whitespace(text)
    working = _LEADING_ENUMERATOR.sub("", original)
    # "41. Appeal against order of District Commission.—Any person…" → drop the heading, the
    # website already shows it as the clause heading.
    heading = _HEADING_DASH.match(working)
    if heading and len(heading.group(1).split()) <= 12:
        working = working[heading.end() :]

    working, terms = _apply_terms(working)
    working, numbers_rewritten = _numbers_as_digits(working)
    working = _DOUBLED_ARTICLE.sub(lambda m: m.group(2), working)

    sentences: list[str] = []
    for sentence in split_sentences(working):
        sentences += _split_long_sentence(sentence)
    working = " ".join(sentences[:MAX_SIMPLIFIED_SENTENCES])
    working = normalize_whitespace(working)
    if working[:1].islower():
        working = working[:1].upper() + working[1:]
    return Simplified(
        original=original, simple=working, terms=terms, numbers_rewritten=numbers_rewritten
    )
