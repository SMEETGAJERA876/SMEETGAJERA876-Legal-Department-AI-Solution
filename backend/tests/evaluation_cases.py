"""Evaluation cases: questions people ask, and where the answer must be found.

Used by tests/test_evaluation.py (automated) and scripts/evaluate.py (printed report
against a running server). Pages refer to the sample PDFs in samples/.
"""

from dataclasses import dataclass
from typing import Literal

SampleName = Literal["employment", "public_notice", "tenancy_rules"]

SAMPLE_FILES: dict[SampleName, str] = {
    "employment": "employment_agreement.pdf",
    "public_notice": "government_public_notice.pdf",
    "tenancy_rules": "tenancy_rules.pdf",
}


@dataclass(frozen=True)
class Case:
    sample: SampleName
    action: Literal["ask", "exact", "semantic"]
    query: str
    page: int | None = None  # page the first answer/result must point to
    contains: str | None = None  # text that must appear in the answer / top result
    fact: str | None = None  # a fact value that must be listed with search results
    found: bool = True
    kind: Literal["document", "about"] = "document"


CASES: list[Case] = [
    # --- Employment agreement (contract) ---
    Case("employment", "ask", "What is my notice period?", page=7, contains="90 days"),
    Case("employment", "exact", "notice pperiod", page=7, fact="90 days"),
    Case("employment", "semantic", "notice period", page=7, fact="within 30 days"),
    Case("employment", "semantic", "What notice do I need before leaving?", page=7),
    Case("employment", "ask", "What happens if I leave early?", page=8),
    Case("employment", "ask", "How much is my salary?", page=4, contains="1,20,000"),
    Case("employment", "ask", "Can the agreement be renewed?", page=9),
    Case("employment", "ask", "What is the recipe for chocolate cake?", found=False),
    Case("employment", "ask", "Why should I use this?", kind="about"),
    Case(
        "employment", "ask", "Why can't I do this using a normal general purpose assistant?",
        kind="about",
    ),
    # --- Government public notice ---
    Case("public_notice", "ask", "What is the last date to apply?", page=3,
         contains="30 April 2026"),
    Case("public_notice", "ask", "What documents do I need to attach?", page=2),
    Case("public_notice", "ask", "How much is the application fee?", page=4, contains="250"),
    Case("public_notice", "ask", "How can I appeal against the decision?", page=5),
    Case("public_notice", "ask", "How much notice will I get before an inspection?", page=3,
         contains="7 days"),
    Case("public_notice", "ask", "Who do I contact for help?", page=5),
    Case("public_notice", "ask", "What happens if I don't pay on time?", page=4),
    Case("public_notice", "semantic", "notice period", fact="within 15 days"),
    Case("public_notice", "exact", "importnt note", page=4),
    Case("public_notice", "ask", "why should i use this?", kind="about"),
    # --- Tenancy rules (Act / Rules format) ---
    Case("tenancy_rules", "ask", "How much notice must the landlord give?", page=2,
         contains="3 months"),
    Case("tenancy_rules", "ask", "When will my security deposit be refunded?", page=3),
    Case("tenancy_rules", "ask", "Where can I appeal against an order of the Rent Authority?",
         page=4),
    Case("tenancy_rules", "ask", "What is the penalty for cutting off water?", page=4),
    Case("tenancy_rules", "exact", "notice", page=2),
]  # fmt: skip


def check(case: Case, body: dict[str, object]) -> list[str]:
    """Return the problems found in an API response for this case (empty = pass)."""
    problems: list[str] = []
    if case.action == "ask":
        citations = body.get("citations") or []
        assert isinstance(citations, list)
        if body.get("kind") != case.kind:
            problems.append(f"expected a {case.kind} answer, got {body.get('kind')}")
        if body.get("found") != case.found:
            problems.append(f"expected found={case.found}, got {body.get('found')}")
        first_page = citations[0]["page_number"] if citations else None
        text = str(body.get("answer", ""))
    else:
        results = body.get("results") or []
        assert isinstance(results, list)
        first_page = results[0]["page_number"] if results else None
        text = str(results[0]["snippet"]) if results else ""
        facts = body.get("facts") or []
        assert isinstance(facts, list)
        if case.fact and not any(case.fact in str(f["value"]) for f in facts):
            problems.append(f"fact '{case.fact}' not listed")
    if case.page is not None and first_page != case.page:
        problems.append(f"expected page {case.page}, got {first_page}")
    if case.contains and case.contains not in text:
        problems.append(f"'{case.contains}' missing from: {text[:120]}")
    return problems
