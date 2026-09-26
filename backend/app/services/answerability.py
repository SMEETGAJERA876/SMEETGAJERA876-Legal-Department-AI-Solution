"""Should ClauseLens answer at all? — the guard against confident answers the document can't
support ("What is the penalty for drunk driving?" asked of the Consumer Protection Act).

Two independent checks; either one saying "no" means the answer is "not found":

1. Subject coverage — the question's specific subject words (not question words or generic
   legal words like "penalty" or "time limit") must actually occur in the document, directly
   or through the plain-language glossary ("builder" → "promoter").
2. Relevance — the cross-encoder must judge the best passage relevant (reranker.py).
"""

import re
from dataclasses import dataclass

from app.services import glossary

# Below this cross-encoder score the best passage does not answer the question. Calibrated on
# the dev split of tests/real_document_cases.py (MiniLM-L-6 scores range roughly -11 … +10).
MIN_RELEVANCE = -7.0
# At or above this the best passage is trusted without the subject-word check. Unanswerable
# questions in the evaluation sets peaked at about -3.2.
STRONG_RELEVANCE = 3.0
MIN_SUBJECT_COVERAGE = 0.5
MIN_WORD_LENGTH = 3
MIN_STEM_LENGTH = 4
STEM_TRIM = 3

# Words that say nothing about *what* the question is about.
GENERIC = frozenset(
    """
what which who whom whose when where why how many much long does do did done can could should
would will shall may might must is are was were be been being the a an of to for in on at by
with from about into onto if or and not no any all some my me mine i you your yours our we they
their them it its this that these those there here get gets got give gives given happen happens
someone somebody anyone anybody person people persons thing things time times limit limits day
days week weeks month months year years rate rates amount amounts fee fees fine fines penalty
penalties punishment rule rules law laws act acts section sections clause clauses document
legal legally right rights allowed allow valid invalid eligible need needs needed required
require have has had file filed filing apply applied ask asked asking pay paid paying money
does doing make makes made take takes taken under per than then also only just like same other
more less least most first last new old way ways kind type case cases matter can't don't
doesn't won't isn't aren't i'm i've tell know want wants going go goes come comes after before
""".split()
)


@dataclass(frozen=True)
class Coverage:
    subject_words: list[str]
    covered: list[str]

    @property
    def ratio(self) -> float:
        return len(self.covered) / len(self.subject_words) if self.subject_words else 1.0

    @property
    def sufficient(self) -> bool:
        return self.ratio >= MIN_SUBJECT_COVERAGE


def _stem(word: str) -> str:
    return word[: max(MIN_STEM_LENGTH, len(word) - STEM_TRIM)]


def _in_vocabulary(word: str, vocabulary: set[str]) -> bool:
    if word in vocabulary:
        return True
    stem = _stem(word)
    return any(v.startswith(stem) for v in vocabulary)


def subject_coverage(question: str, vocabulary: set[str]) -> Coverage:
    text = question.lower()
    subject: list[str] = []
    covered: list[str] = []
    # Everyday phrases the glossary knows count as covered when the document uses them or
    # their legal wording ("salary" in a job offer, "wages" in the Code on Wages).
    for phrase in dict.fromkeys(glossary.plain_phrases(text)):
        text = text.replace(phrase, " ")
        if all(w in GENERIC for w in re.findall(r"[a-z']+", phrase)):
            continue  # "punishment", "fine", "time limit" say nothing about the subject
        subject.append(phrase)
        wordings = [phrase, *glossary.legal_terms(phrase)]
        if any(all(_in_vocabulary(w, vocabulary) for w in re.findall(r"[a-z]+", t.lower()))
               for t in wordings):  # fmt: skip
            covered.append(phrase)
    for word in dict.fromkeys(re.findall(r"[a-z][a-z'-]+", text)):
        if len(word) < MIN_WORD_LENGTH or word in GENERIC:
            continue
        subject.append(word)
        if _in_vocabulary(word, vocabulary):
            covered.append(word)
    return Coverage(subject, covered)


def answerable(question: str, vocabulary: set[str], best_relevance: float | None) -> bool:
    # A passage the cross-encoder is confident about answers the question even when the
    # question words differ from the document's ("cancel a gift" vs "transfer … void").
    if best_relevance is not None and best_relevance >= STRONG_RELEVANCE:
        return True
    if not subject_coverage(question, vocabulary).sufficient:
        return False
    return best_relevance is None or best_relevance >= MIN_RELEVANCE
