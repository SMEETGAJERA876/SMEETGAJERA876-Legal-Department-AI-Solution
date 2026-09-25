"""Answers to questions about ClauseLens itself ("Why should I use this?").

These are not claims about the uploaded document, so they are labelled as information
about the tool and never presented as document evidence.
"""

import re
from dataclasses import dataclass

_ABOUT_PATTERNS = [
    r"\bwhy\s+(?:should|would|do|must)\s+(?:i|we|someone|anyone)\s+use\b",
    r"\bwhy\s+(?:use|choose|pick)\s+(?:this|it|you|clauselens)\b",
    r"\bwhy\s+(?:can'?t|cannot|can\s+not|shouldn'?t|not)\s+(?:i|we)\b.*\b(?:assistant|chatbot|"
    r"chat\s?gpt|gemini|copilot|claude|ai|tool|general)",
    r"\bgeneral[\s-]*purpose\b",
    r"\b(?:chat\s?gpt|gemini|copilot|bard|perplexity)\b",
    r"\b(?:normal|regular|other|any|ordinary|generic)\s+(?:ai|assistant|chatbot|chat\s?bot|tool|llm)\b",
    r"\bwhat\s+(?:is|does)\s+(?:this|clauselens)(?:\s+(?:app|tool|website|site|product))?\s*"
    r"(?:do|for|about)?\s*\??$",
    r"\bhow\s+(?:is|does)\s+(?:this|clauselens)\s+(?:app\s+|tool\s+)?(?:work|different|better)",
    r"\bwhat\s+makes\s+(?:this|clauselens|you)\s+(?:different|better|special)",
    r"\b(?:benefits?|advantages?)\s+of\s+(?:this|using\s+this|clauselens)\b",
    r"\b(?:are|is)\s+(?:you|this|clauselens)\s+(?:a\s+)?lawyer\b",
    r"\bcan\s+(?:i|we)\s+trust\s+(?:this|you|clauselens|the\s+answers?)\b",
]
_ABOUT_REGEX = re.compile("|".join(f"(?:{p})" for p in _ABOUT_PATTERNS), re.IGNORECASE)
_COMPARISON_REGEX = re.compile(
    r"general[\s-]*purpose|chat\s?gpt|gemini|copilot|bard|perplexity|assistant|chatbot|"
    r"normal|regular|other|ordinary|generic|different|better",
    re.IGNORECASE,
)
_LAWYER_REGEX = re.compile(r"\blawyer\b|\btrust\b", re.IGNORECASE)


@dataclass(frozen=True)
class AboutAnswer:
    answer: str
    points: list[str]
    note: str


def is_about_question(question: str) -> bool:
    return bool(_ABOUT_REGEX.search(question))


def _document_line(page_count: int | None, fact_count: int, clause_count: int) -> str:
    if not page_count:
        return ""
    return (
        f" For this document, it has already read all {page_count} pages, found "
        f"{clause_count} clauses and pulled out {fact_count} key details, each linked to its page."
    )


WHY_USE_POINTS = [
    "Finds what matters quickly: notice periods, deadlines, amounts, dates, penalties, "
    "appeals and notes are listed automatically, each with its page and clause.",
    "Search by meaning or by exact words — even with typos. Asking about a “notice period” "
    "also shows every time limit and note in the document.",
    "Every answer shows the page and clause, and one click opens the page with the exact "
    "wording highlighted, so you can check it yourself.",
    "It says when the document does not answer your question instead of guessing.",
    "It prepares a list of questions to discuss with a qualified legal professional.",
]

COMPARISON_POINTS = [
    "Grounded in your document only: answers are built from passages retrieved from the "
    "uploaded file, and every quote is checked against the document before it is shown. A "
    "general-purpose assistant can mix in general knowledge or assumptions without telling you.",
    "Verifiable in one click: citations open the exact page with the wording highlighted. With "
    "a general assistant you have to find the passage yourself, and quoted page numbers can be "
    "wrong.",
    "Honest when information is missing: if the document does not say something, ClauseLens "
    "says so rather than producing a plausible-sounding answer.",
    "Built for long documents: the whole file is indexed page by page, so nothing is cut off "
    "and every answer can be traced back to its page.",
    "Structured overview: key terms (notice periods, deadlines, fees, penalties, appeals, "
    "notes) are extracted once and kept with their sources.",
    "Private by default: your document and its search index stay on this server. When the "
    "optional AI explanations are switched on, only the few relevant excerpts are sent.",
]

LAWYER_POINTS = [
    "ClauseLens is not a lawyer and does not give legal advice.",
    "It shows what the document says, where it says it, and explains it in simple language.",
    "Always check the highlighted source, and discuss important decisions with a qualified "
    "legal professional — the “Questions to ask a legal professional” button helps you prepare.",
]

ABOUT_NOTE = "This answer is about ClauseLens itself, not about your document."


def answer_about(
    question: str, page_count: int | None, fact_count: int, clause_count: int
) -> AboutAnswer:
    document_line = _document_line(page_count, fact_count, clause_count)
    if _LAWYER_REGEX.search(question):
        return AboutAnswer(
            "ClauseLens helps you understand and navigate your document — it is not a lawyer.",
            LAWYER_POINTS,
            ABOUT_NOTE,
        )
    if _COMPARISON_REGEX.search(question):
        return AboutAnswer(
            "A general-purpose assistant can read a PDF, but ClauseLens is built so you can "
            "trust and check every answer about your document." + document_line,
            COMPARISON_POINTS,
            ABOUT_NOTE,
        )
    return AboutAnswer(
        "ClauseLens turns a long legal or government document into answers you can check: "
        "it finds the important parts, explains them, and takes you to the exact place in "
        "the document." + document_line,
        WHY_USE_POINTS,
        ABOUT_NOTE,
    )
