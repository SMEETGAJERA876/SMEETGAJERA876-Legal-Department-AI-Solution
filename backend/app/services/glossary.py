"""Plain-language glossary (data/taxonomy/plain_language.json).

People ask "Will I get my money back if the builder delays possession?"; the Act says
"promoter", "allottee" and "return of amount". The glossary maps one to the other so search
can find the right passage and the answerability check can tell whether a topic is covered.
"""

import re
from functools import lru_cache

from app.services import taxonomy


@lru_cache
def _entries() -> tuple[tuple[re.Pattern[str], tuple[str, ...]], ...]:
    entries = []
    for term in taxonomy.load("plain_language.json")["terms"]:
        plain = sorted(term["plain"], key=len, reverse=True)
        pattern = re.compile(r"\b(?:" + "|".join(re.escape(p) for p in plain) + r")\b", re.I)
        entries.append((pattern, tuple(term["legal"])))
    return tuple(entries)


def legal_terms(question: str) -> list[str]:
    """Legal wording for the everyday words in the question, most specific entries first."""
    found: list[str] = []
    for pattern, legal in _entries():
        if pattern.search(question):
            found += [t for t in legal if t not in found]
    return found


def plain_phrases(question: str) -> list[str]:
    """The everyday phrases the glossary recognised in the question (e.g. "builder")."""
    return [m.group(0).lower() for pattern, _ in _entries() for m in pattern.finditer(question)]
