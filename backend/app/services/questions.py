"""Questions a user may want to discuss with a qualified legal professional.

Each question is tied to a fact found in the document, so it always has a source.
"""

from dataclasses import dataclass

from app.models import LegalFact

TEMPLATES: dict[str, tuple[str, ...]] = {
    "notice_period": (
        "What happens if I can't give the full {value} of notice?",
        "Does the {value} notice have to be in writing, and who must it be sent to?",
    ),
    "termination": (
        "In what situations can the other party end this agreement early, and what would "
        "I be owed?",
    ),
    "penalty": ("How would the charges described here be calculated, and can they be negotiated?",),
    "payment": ("Are there any costs besides {value} that I could be asked to pay?",),
    "renewal": ("Does this agreement renew automatically, and how can I stop a renewal?",),
    "duration": ("What happens when the {value} term ends?",),
    "confidentiality": (
        "How long do the confidentiality obligations last after the agreement ends?",
    ),
    "dispute_resolution": ("If there is a disagreement, where and how would it be resolved?",),
    "liability": ("Is there a limit on how much I could be held responsible for?",),
    "obligations": ("Which of my responsibilities in this document are most important to meet?",),
    "probation": ("What happens at the end of the {value} probation, and can it be extended?",),
    "deposit": ("When and how will the {value} deposit be returned, and what can be deducted?",),
    "late_fee": ("How is the late fee of {value} applied, and is there a grace period?",),
    "interest_rate": ("How is interest of {value} calculated, and from which date?",),
    "non_compete": (
        "Is the non-compete restriction reasonable and enforceable where I live and work?",
    ),
    "non_solicitation": (
        "Which clients or colleagues does the non-solicitation clause cover, and for how long?",
    ),
    "arbitration": ("How would arbitration work in practice, and who pays its costs?",),
    "cure_period": (
        "If I am told I have breached the agreement, how do I use the {value} to fix it?",
    ),
    "intellectual_property": (
        "Does the intellectual property clause cover work I do in my own time?",
    ),
    "time_limits": ("What happens if I miss the deadline ({value})? Can it be extended?",),
    "appeal": (
        "What should an appeal or complaint include, and what happens while it is pending?",
    ),
    "documents_required": (
        "Are copies or originals needed, and what if I can't get one of these documents?",
    ),
    "eligibility": ("Do I meet the eligibility conditions described here, and how can I show it?",),
    "notes": ("Does this note change any of my obligations or deadlines?",),
    "authority": ("Which office should I contact first if something goes wrong?",),
    "rights": ("How do I use this right in practice, and what can I do if it is refused?",),
}
MAX_QUESTIONS = 10
# Concepts where each distinct value deserves its own questions (e.g. 90 vs 14 days).
REPEAT_PER_VALUE = {"notice_period"}
PRIORITY = [
    "termination", "notice_period", "probation", "time_limits", "penalty", "payment",
    "deposit", "late_fee", "non_compete", "appeal",
    "documents_required", "eligibility", "renewal", "duration", "notes",
]  # fmt: skip


@dataclass
class ProfessionalQuestion:
    question: str
    concept: str
    fact: LegalFact


def generate_questions(facts: list[LegalFact]) -> list[ProfessionalQuestion]:
    questions: list[ProfessionalQuestion] = []
    seen: set[str] = set()
    for fact in facts:
        for template in TEMPLATES.get(fact.concept, ()):
            # Value-specific templates repeat per value; generic ones appear once per concept.
            text = template.format(value=fact.value)
            key = text if fact.concept in REPEAT_PER_VALUE else template
            if key in seen:
                continue
            seen.add(key)
            questions.append(ProfessionalQuestion(text, fact.concept, fact))
    questions.sort(key=lambda q: PRIORITY.index(q.concept) if q.concept in PRIORITY else 99)
    return questions[:MAX_QUESTIONS]
