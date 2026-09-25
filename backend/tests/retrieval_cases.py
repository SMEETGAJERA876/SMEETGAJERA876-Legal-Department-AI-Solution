"""Retrieval evaluation cases: query → where the answer is (page, and clause prefix).

A result is relevant when it is on one of `pages` and, if `clauses` is given, its clause
reference starts with one of them ("12" matches 12.1, 12.2 …; "Rule 7" matches Rule 7(1)).
"""

from dataclasses import dataclass

from tests.evaluation_cases import SampleName


@dataclass(frozen=True)
class RetrievalCase:
    sample: SampleName
    query: str
    pages: tuple[int, ...]
    clauses: tuple[str, ...] = ()


CASES: list[RetrievalCase] = [
    # --- employment agreement
    # the agreement has two notice periods: 14 days in probation (4.1) and 90 days (12.1)
    RetrievalCase("employment", "notice period", (2, 7), ("4.1", "12")),
    RetrievalCase("employment", "What notice do I need before leaving?", (7,), ("12",)),
    RetrievalCase("employment", "Clause 13", (8,), ("13",)),
    RetrievalCase("employment", "gross misconduct", (7,), ("12.3",)),
    RetrievalCase("employment", "Can I be fired immediately?", (7,), ("12.3",)),
    RetrievalCase("employment", "salary in lieu of notice", (7,), ("12.2",)),
    RetrievalCase("employment", "reimbursement of expenses", (4,), ("7",)),
    RetrievalCase("employment", "Who owns the work I create?", (6,), ("10",)),
    RetrievalCase("employment", "Can I contact clients after leaving?", (6,), ("11",)),
    RetrievalCase("employment", "Where are disputes decided?", (10,), ("16",)),
    RetrievalCase("employment", "bonus", (4,), ("6.2",)),
    RetrievalCase("employment", "training costs", (8,), ("13.2",)),
    RetrievalCase("employment", "Senior Data Analyst", (1,), ("2",)),
    RetrievalCase("employment", "automatic renewal", (9,), ("14",)),
    # --- government public notice
    RetrievalCase("public_notice", "REV/2026/114", (1,)),
    RetrievalCase("public_notice", "Deputy Commissioner", (5,), ("6",)),
    RetrievalCase("public_notice", "1800-000-0000", (5,), ("7",)),
    RetrievalCase("public_notice", "sale deed", (2,), ("3",)),
    RetrievalCase("public_notice", "Who cannot apply?", (2,), ("2.2",)),
    RetrievalCase("public_notice", "site inspection", (3,), ("4.3",)),
    RetrievalCase("public_notice", "What if my application is incomplete?", (4,)),
    # --- tenancy rules
    RetrievalCase("tenancy_rules", "Rule 7", (3,), ("Rule 7",)),
    RetrievalCase("tenancy_rules", "How often can the rent be increased?", (3,), ("Rule 7",)),
    RetrievalCase("tenancy_rules", "Rent Tribunal", (4,), ("Rule 9",)),
    RetrievalCase("tenancy_rules", "cut off water or electricity", (4,), ("Rule 10",)),
    RetrievalCase("tenancy_rules", "definition of tenant", (1,), ("Rule 2",)),
    RetrievalCase("tenancy_rules", "security deposit refund", (3,), ("Rule 6",)),
]


def is_relevant(case: RetrievalCase, page: int, clause_ref: str | None) -> bool:
    if page not in case.pages:
        return False
    if not case.clauses:
        return True
    return clause_ref is not None and any(clause_ref.startswith(c) for c in case.clauses)
