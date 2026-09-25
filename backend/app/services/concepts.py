"""Legal concept vocabulary and rule-based fact extraction.

Covers contracts and government documents (notices, circulars, orders, schemes, acts and
rules, applications, tenders, court orders). Every extracted fact keeps the exact sentence
it came from, so nothing is invented.
"""

import difflib
import re
from dataclasses import dataclass

from spellchecker import SpellChecker


@dataclass(frozen=True)
class Concept:
    key: str
    label: str
    keywords: tuple[str, ...]  # phrases that mark a sentence as being about the concept
    question_triggers: tuple[str, ...]  # everyday words people use when asking about it
    related: tuple[str, ...]


def _words(spec: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in spec.split("|") if part.strip())


def _concept(key: str, label: str, keywords: str, triggers: str, related: str) -> Concept:
    return Concept(key, label, _words(keywords), _words(triggers), _words(related))


CONCEPTS: dict[str, Concept] = {
    c.key: c
    for c in [
        # --- specific concepts first: a question names the most specific one first
        _concept(
            "probation",
            "Probation",
            "probation|probationary",
            "probation|trial period|on probation",
            "notice_period|termination|salary",
        ),
        _concept(
            "salary",
            "Salary",
            "salary|ctc|wages|gross pay|basic pay|stipend|remuneration",
            "salary|ctc|wage|stipend|earn|compensation",
            "payment|leave|working_hours",
        ),
        _concept(
            "rent",
            "Rent",
            "rent|licence fee|license fee",
            "the rent|monthly rent|rent amount|pay rent|rent is|rent of|how much rent|licence fee",
            "deposit|payment|late_fee",
        ),
        _concept(
            "deposit",
            "Deposit",
            "deposit|security amount|advance",
            "deposit|security amount|advance amount",
            "rent|payment|termination",
        ),
        _concept(
            "late_fee",
            "Late fee",
            "late fee|late payment|delayed payment|late charge",
            "late fee|late payment|pay late|delayed payment",
            "interest_rate|penalty|payment",
        ),
        _concept(
            "interest_rate",
            "Interest rate",
            "interest|per annum|p.a.",
            "interest|rate of interest|interest rate",
            "late_fee|payment|penalty",
        ),
        _concept(
            "working_hours",
            "Working hours",
            "working hours|hours per week|hours a week|hours per day|core hours|shift",
            "working hours|work hours|hours|shift|timing",
            "leave|salary",
        ),
        _concept(
            "leave",
            "Leave",
            "paid leave|sick leave|casual leave|annual leave|earned leave|days of leave"
            "|holiday|vacation",
            "paid leave|sick leave|casual leave|annual leave|earned leave|leave days|leave policy"
            "|leave entitlement|how many leaves|holiday|vacation|days off|time off",
            "working_hours|salary",
        ),
        _concept(
            "job_title",
            "Job title",
            "designation|position of|appointed as|role of",
            "designation|job title|position|my role|appointed as",
            "salary|obligations",
        ),
        _concept(
            "area",
            "Area",
            "sq. ft|sq ft|square feet|square metres|square meters|sq. m|acres|hectares",
            "area|size|square feet|sq ft|how big",
            "rent|deposit",
        ),
        _concept(
            "governing_law",
            "Governing law",
            "governed by|governing law|laws of",
            "governing law|which law|laws of|law applies",
            "jurisdiction|arbitration|dispute_resolution",
        ),
        _concept(
            "jurisdiction",
            "Jurisdiction",
            "jurisdiction|courts at|courts of|courts in",
            "jurisdiction|which court|where can i sue|courts",
            "governing_law|arbitration|dispute_resolution",
        ),
        _concept(
            "arbitration",
            "Arbitration",
            "arbitration|arbitrator|arbitral",
            "arbitration|arbitrator",
            "jurisdiction|governing_law|dispute_resolution",
        ),
        _concept(
            "cure_period",
            "Time to fix a breach",
            "cure|remedy the breach|rectify",
            "cure period|fix a breach|remedy|rectify",
            "termination|notice_period",
        ),
        _concept(
            "reference_number",
            "Reference number",
            "ref|reference|no.|order no|notification no|file no",
            "reference number|ref no|order number|notification number|file number",
            "effective_date|authority",
        ),
        _concept(
            "effective_date",
            "Effective date",
            "with effect from|w.e.f|effective from|effective date|come into force|comes into force",
            "effective date|comes into force|come into force|start date|with effect from"
            "|when does it start",
            "important_dates|duration",
        ),
        _concept(
            "contact",
            "Contact details",
            "helpline|phone|telephone|email|e-mail|contact",
            "contact|phone|email|helpline|call|reach",
            "authority|appeal",
        ),
        _concept(
            "court_name",
            "Court",
            "court|tribunal",
            "which court|court name|tribunal",
            "case_number|appeal",
        ),
        _concept(
            "case_number",
            "Case number",
            "case no|w.p. no|petition no|appeal no|suit no",
            "case number|case no|petition number",
            "court_name|appeal",
        ),
        _concept(
            "intellectual_property",
            "Intellectual property",
            "intellectual property|work product|copyright|patent|trademark|moral rights",
            "intellectual property|copyright|who owns|ownership of work|patent|ip",
            "confidentiality|termination",
        ),
        _concept(
            "indemnification",
            "Indemnity",
            "indemnify|indemnification|indemnity|hold harmless",
            "indemnity|indemnify|indemnification|hold harmless",
            "liability|dispute_resolution",
        ),
        _concept(
            "force_majeure",
            "Force majeure",
            "force majeure|act of god|beyond the reasonable control|beyond reasonable control",
            "force majeure|act of god|natural disaster|pandemic|beyond my control",
            "termination|liability",
        ),
        _concept(
            "assignment",
            "Transfer of the agreement",
            "assign this agreement|shall not assign|assignment of this|may assign"
            "|assign its rights",
            "assign|assignment|transfer the agreement",
            "termination|obligations",
        ),
        _concept(
            "non_compete",
            "Non-compete",
            "non-compete|non compete|shall not engage|competing business|compete with",
            "non-compete|non compete|compete|competitor|work for a competitor",
            "non_solicitation|confidentiality|termination",
        ),
        _concept(
            "non_solicitation",
            "Non-solicitation",
            "solicit|non-solicitation|poach",
            "solicit|non-solicitation|poach|approach clients|hire staff",
            "non_compete|confidentiality",
        ),
        _concept(
            "notice_period",
            "Notice period",
            "notice period|days' notice|days notice|written notice|prior notice|advance notice"
            "|months' notice|weeks' notice|notice of|prior intimation|intimation",
            "notice|leave|leaving|quit|resign|exit|warn|intimat",
            "time_limits|termination|penalty|notes",
        ),
        _concept(
            "time_limits",
            "Deadlines and time limits",
            "within|not later than|no later than|on or before|last date|due date|deadline"
            "|from the date of|time limit|prior to",
            "deadline|last date|time limit|within|how many days|by when|how long do i have|due"
            "|submit|time|when should|when must|period|how soon|late",
            "important_dates|notice_period|penalty",
        ),
        _concept(
            "important_dates",
            "Important dates",
            "",
            "when|date|deadline|valid",
            "time_limits|duration|renewal",
        ),
        _concept(
            "notes",
            "Important notes",
            "note:|n.b.|please note|important:|important note|attention|it is hereby notified"
            "|notice is hereby given|it is clarified|disclaimer",
            "note|notes|important|remark|n.b|nb|warning|caution|attention",
            "notice_period|time_limits|obligations",
        ),
        _concept(
            "termination",
            "Ending the agreement",
            "terminate|termination|resign|resignation|dismiss|cancel|revoke|revocation|withdraw",
            "terminate|termination|leave|leaving|quit|end the|cancel|exit|early|fire|fired"
            "|dismiss|resign|revoke|withdraw",
            "notice_period|penalty|renewal|duration|payment",
        ),
        _concept(
            "duration",
            "How long it lasts",
            "term of|duration|commence|shall remain in|period of|expire|expiry|valid for"
            "|validity|valid till|valid until|in force",
            "how long|duration|expire|expiry|end date|start|term|last|valid|validity",
            "renewal|termination|important_dates",
        ),
        _concept(
            "payment",
            "Money, fees and payments",
            "pay|payment|salary|fee|fees|rent|invoice|compensation|remuneration|deposit|price"
            "|wage|bonus|reimburse|charges|stamp duty|tax|amount|cost|subsidy|grant|refund",
            "pay|payment|money|cost|salary|fee|rent|deposit|how much|price|owe|bonus|charge"
            "|tax|amount|refund|subsidy",
            "penalty|termination|obligations",
        ),
        _concept(
            "renewal",
            "Renewal",
            "renew|renewal|extend|extension|automatically continue",
            "renew|renewal|extend|extension|continue after",
            "duration|termination|notice_period",
        ),
        _concept(
            "penalty",
            "Penalties and consequences",
            "penalty|liquidated damages|forfeit|late fee|interest on|fine|deduct|imprisonment"
            "|punishable|prosecution|disqualif|blacklist|shall be rejected|liable to be",
            "penalty|fine|charge|forfeit|late|break|early|punish|jail|consequence|reject"
            "|what happens if",
            "termination|payment|notice_period|time_limits",
        ),
        _concept(
            "obligations",
            "Responsibilities",
            "shall be responsible|responsible for|obligation|duties|agrees to|shall maintain"
            "|maintenance|is required to|are required to|shall submit|mandatory|shall ensure"
            "|shall comply",
            "responsible|responsibility|obligation|duty|duties|must i|maintenance|who pays"
            "|required|mandatory|have to",
            "payment|liability|time_limits",
        ),
        _concept(
            "eligibility",
            "Eligibility",
            "eligible|eligibility|qualif|criteria|age limit|shall be entitled|who can apply",
            "eligible|eligibility|qualify|who can apply|criteria|entitled|can i apply",
            "documents_required|time_limits|payment",
        ),
        _concept(
            "documents_required",
            "Documents required",
            "documents required|following documents|enclose|attach|copy of|proof of"
            "|self-attested|certificate|supporting documents",
            "documents|what do i need|attach|proof|certificate|papers|enclose",
            "eligibility|time_limits",
        ),
        _concept(
            "appeal",
            "Appeals and complaints",
            "appeal|appellate|grievance|complaint|representation|review petition|redress|objection",
            "appeal|complain|complaint|grievance|challenge|rejected|object|objection",
            "time_limits|authority",
        ),
        _concept(
            "authority",
            "Authority and contact",
            "officer|authority|commissioner|department|contact|helpline|email|e-mail|phone"
            "|telephone|address for|office of",
            "contact|who do i|whom|which office|authority|officer|address|phone|email"
            "|helpline|who issued",
            "appeal|documents_required",
        ),
        _concept(
            "rights",
            "Your rights",
            "right to|entitled to|may request|may apply|shall be provided|shall be given",
            "right|rights|entitled|allowed|am i allowed",
            "obligations|appeal",
        ),
        _concept(
            "dispute_resolution",
            "Resolving disputes",
            "dispute|arbitration|arbitrator|jurisdiction|governing law|mediation|courts of",
            "dispute|disagree|court|arbitration|sue|law|conflict",
            "liability|termination|appeal",
        ),
        _concept(
            "confidentiality",
            "Confidentiality",
            "confidential|non-disclosure|proprietary|trade secret",
            "confidential|secret|disclose|share information|nda|privacy",
            "obligations|termination",
        ),
        _concept(
            "liability",
            "Liability and damages",
            "liable|liability|indemnif|damages|limitation of liability",
            "liable|liability|damage|responsible if|indemn|sued|blame",
            "penalty|dispute_resolution|obligations",
        ),
        _concept("parties", "Parties", "", "who are the parties|parties|between", ""),
    ]
}

# Searching one concept also surfaces facts of the same "type": e.g. "notice period"
# also lists every time limit and important note in the document.
SEARCH_FAMILIES: dict[str, tuple[str, ...]] = {
    "notice_period": ("notice_period", "time_limits", "notes"),
    "time_limits": ("time_limits", "notice_period", "important_dates"),
    "important_dates": ("important_dates", "time_limits"),
    "notes": ("notes", "notice_period"),
    "payment": ("payment", "penalty"),
    "penalty": ("penalty", "payment"),
    "appeal": ("appeal", "time_limits", "authority"),
}

_TRIGGER_VOCABULARY = sorted(
    {word for c in CONCEPTS.values() for t in c.question_triggers for word in t.split()}
    | {word for c in CONCEPTS.values() for k in c.keywords for word in re.findall(r"[a-z]+", k)}
)
MIN_FUZZY_WORD_LENGTH = 4
FUZZY_CUTOFF = 0.8


def _english() -> SpellChecker:
    from app.services.document_check import _speller  # shared, loaded once

    return _speller()


def correct_spelling(text: str, vocabulary: set[str] | None = None) -> str:
    """Fix likely typos ("notice pperiod" → "notice period") against known words."""
    known = set(_TRIGGER_VOCABULARY) | (vocabulary or set())
    candidates = sorted(known)

    def fix(match: re.Match[str]) -> str:
        word = match.group(0)
        lowered = word.lower()
        if len(lowered) < MIN_FUZZY_WORD_LENGTH or lowered in known:
            return word
        if not _english().unknown([lowered]):
            return word  # a real word ("contract") is not a typo of another ("contact")
        close = difflib.get_close_matches(lowered, candidates, n=1, cutoff=FUZZY_CUTOFF)
        return close[0] if close else word

    return re.sub(r"[A-Za-z]+", fix, text)


def detect_query_concepts(question: str) -> list[str]:
    text = f" {correct_spelling(question).lower()} "
    return [c.key for c in CONCEPTS.values() if any(t in text for t in c.question_triggers)]


def search_family(concept_keys: list[str]) -> list[str]:
    family: list[str] = []
    for key in concept_keys:
        for member in SEARCH_FAMILIES.get(key, (key,)):
            if member not in family:
                family.append(member)
    return family


def related_concepts(concept_keys: list[str]) -> list[str]:
    related: list[str] = []
    for key in concept_keys:
        for other in CONCEPTS[key].related:
            if other not in concept_keys and other not in related:
                related.append(other)
    return related


def heading_matches(heading: str | None, concept_keys: list[str]) -> bool:
    if not heading:
        return False
    lowered = heading.lower()
    return any(
        kw in lowered or key.replace("_", " ") in lowered
        for key in concept_keys
        for kw in CONCEPTS[key].keywords
    )


def concept_keyword_hits(text: str, concept_keys: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for key in concept_keys for kw in CONCEPTS[key].keywords if kw in lowered)
