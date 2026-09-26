"""Document classification: which taxonomy type is this document? (docs/Document_Classification.md)

Rule-based and explainable. Every type in data/taxonomy/document_types.json is scored from:

  1. title keywords (first ~400 characters — the letterhead and title)        strongest
  2. structural markers ("CORAM", "these rules may be called", …)             strong
  3. keywords elsewhere on the first page                                     medium
  4. party roles (Employer/Employee, Landlord/Tenant, Petitioner/Respondent)  category-level
  5. the issuer (Government of…, Ministry of…) and section headings           supporting

The best score becomes a confidence. A low-confidence result is never forced: the document
type is left empty, the best guesses are offered as alternatives, and the user is asked.
"""

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Literal

from app.services import taxonomy
from app.services.text_utils import normalize_whitespace

TITLE_AREA_CHARS = 400
CLASSIFY_PAGES = 2
TITLE_LINE_WEIGHT = 4.5  # keyword in a heading-style line at the top ("CIRCULAR", "LEASE DEED")
TITLE_WEIGHT = 3.0
TITLE_LINES = 10
MIN_UPPERCASE_SHARE = 0.7
GENERIC_CONFIDENCE = 0.3
FIRST_PAGE_WEIGHT = 1.0
PHRASE_SPECIFICITY = 1.0  # multi-word keywords, e.g. "employment agreement"
WORD_SPECIFICITY = 0.5  # single words, e.g. "tender", "scheme"
CATEGORY_SHARE = 1.0  # a category bonus is added to types of that category that have evidence
SECONDARY_SHARE = 0.5
MIN_SCORE = 1.5  # below this nothing is suggested at all
STRONG_SCORE = 4.5  # a title match plus one corroborating signal
BASE_CONFIDENCE = 0.35
CONFIDENCE_RANGE = 0.6
HIGH, MEDIUM = 0.8, 0.5
MAX_ALTERNATIVES = 3

Level = Literal["high", "medium", "low"]
Status = Literal["confirmed", "needs_review", "unknown", "user_verified"]


@dataclass
class Classification:
    category: str | None
    document_type: str | None
    confidence: float
    confidence_level: Level
    status: Status
    method: Literal["rules", "user"] = "rules"
    signals: list[str] = field(default_factory=list)
    alternatives: list[dict[str, Any]] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        if self.document_type:
            entry = taxonomy.document_type(self.document_type)
            return str(entry["name"]) if entry else self.document_type
        if self.category:
            return f"{taxonomy.category_names()[self.category]} document"
        return "Unknown document type"

    def to_json(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "document_type": self.document_type,
            "confidence": self.confidence,
            "confidence_level": self.confidence_level,
            "status": self.status,
            "method": self.method,
            "signals": self.signals,
            "alternatives": self.alternatives,
        }


# (pattern, type id, bonus, signal shown to the user)
STRUCTURE_RULES: list[tuple[str, str, float, str]] = [
    (r"\bthese rules may be called\b", "policy.rules", 3.0, '"these rules may be called"'),
    (r"\bthese regulations may be called\b", "policy.regulations", 3.0, '"these regulations may be called"'),
    (r"\bbe it enacted\b", "policy.act", 3.0, '"be it enacted"'),
    # Consolidated statutes (India Code): "(ACT NO. 22 OF 2005)" under the title.
    # Only statutes carry a legislature's Act number, so it outweighs title words such as
    # "Data Protection" that also name company policies.
    (r"\(\s*act\s*no\.?\s*\d+\s+of\s+\d{4}\s*\)", "policy.act", 12.0, 'Act number ("Act No. … of …")'),
    (r"\barr\w*\s+of\s+sections\b", "policy.act", 3.0, '"Arrangement of sections"'),
    (r"\bnotice is hereby given\b", "public_notice.public_notice", 2.0, '"notice is hereby given"'),
    (r"\bit is hereby notified\b", "government.notification", 2.0, '"it is hereby notified"'),
    (r"\bapplications are invited\b", "government.recruitment_notification", 2.0, '"applications are invited"'),
    (r"\bcoram\b", "court.judgment", 2.0, '"CORAM" (bench of judges)'),
    (r"\bit is (?:hereby )?ordered\b", "court.order", 1.0, '"it is ordered"'),
    (r"\bsolemnly (?:affirm|state)\b|\bdeponent\b", "court.affidavit", 3.0, "sworn statement wording"),
    (r"\bpleased to offer\b", "employment.offer_letter", 2.0, '"pleased to offer"'),
    (r"\bpleased to appoint\b", "employment.appointment_letter", 2.0, '"pleased to appoint"'),
    (r"\bshow cause\b", "employment.show_cause_notice", 2.0, '"show cause"'),
    (r"\breleased on bail\b|\bbail (?:is|be) granted\b", "court.bail_order", 2.0, "bail wording"),
    (r"\bresolved that\b.{0,60}\bboard\b|\bboard of directors\b.{0,80}\bresolved\b",
     "corporate.board_resolution", 2.0, "board resolution wording"),
    (r"\bthis is to certify\b", "other.certificate", 1.5, '"this is to certify"'),
    (r"\bbill to\b|\binvoice (?:no|number)\b", "financial.invoice", 2.0, "invoice fields"),
]  # fmt: skip

# (patterns that must all appear, category, bonus, signal)
ROLE_RULES: list[tuple[tuple[str, ...], str, float, str]] = [
    ((r"\bemploy(?:er|ee)\b", r"\bemployee\b"), "employment", 1.5, "parties are an employer and an employee"),
    ((r"\b(?:landlord|lessor|licensor)\b", r"\b(?:tenant|lessee|licensee)\b"), "property", 1.5,
     "parties are a landlord and a tenant"),
    ((r"\bborrower\b", r"\blender\b"), "financial", 1.5, "parties are a borrower and a lender"),
    ((r"\b(?:petitioner|plaintiff|appellant|complainant)s?\b", r"\b(?:respondent|defendant|accused)s?\b"),
     "court", 2.0, "petitioner / respondent (a court case)"),
    ((r"\b(?:government of|ministry of|department of|municipal corporation|directorate of)\b",),
     "government", 1.0, "issued by a government body"),
    ((r"\b(?:university|college|school|institute)\b", r"\bstudents?\b"), "education", 1.0,
     "issued by an educational institution"),
    ((r"\b(?:private limited|pvt\.? ltd|limited)\b", r"\bboard of directors\b|\bshareholders?\b"),
     "corporate", 1.5, "company constitution / governance wording"),
]  # fmt: skip

# (section heading words — at least two must be present, type ids, bonus, signal)
HEADING_RULES: list[tuple[tuple[str, ...], tuple[str, ...], float, str]] = [
    (("probation", "salary", "compensation", "termination", "leave", "notice period"),
     ("employment.employment_agreement",), 1.5, "sections: probation / salary / termination"),
    (("eligibility", "last date", "documents required", "how to apply", "fee", "important dates"),
     ("public_notice.public_notice", "government.recruitment_notification"), 1.0,
     "sections: eligibility / last date / documents required"),
    (("rent", "deposit", "security deposit", "maintenance", "premises"),
     ("property.rental_agreement", "property.lease_agreement"), 1.0, "sections: rent / deposit / premises"),
    (("facts", "issues", "arguments", "findings", "order", "analysis"),
     ("court.judgment",), 1.5, "sections: facts / issues / findings"),
    (("definitions", "confidential information", "confidentiality", "permitted use", "return of information"),
     ("legal.nda",), 1.0, "sections: confidential information / permitted use"),
]  # fmt: skip


# Title words too generic to name a type, but enough to suggest a category.
GENERIC_TITLE_WORDS: list[tuple[str, str]] = [
    (r"\bagreement\b", "legal"), (r"\bcontract\b", "legal"), (r"\bdeed\b", "property"),
    (r"\bnotice\b", "public_notice"), (r"\bpolicy\b", "corporate"), (r"\border\b", "government"),
    (r"\bguidelines?\b", "policy"), (r"\bletter\b", "other"),
]  # fmt: skip


def _title_lines(first_page: str) -> str:
    """Heading-style lines near the top, mostly in capitals ("PUBLIC NOTICE", "CIRCULAR No. 4")."""
    lines = []
    for line in first_page.splitlines()[:TITLE_LINES]:
        letters = [ch for ch in line if ch.isalpha()]
        if len(letters) >= 4 and sum(ch.isupper() for ch in letters) >= MIN_UPPERCASE_SHARE * len(
            letters
        ):
            lines.append(normalize_whitespace(line).lower())
    return " | ".join(lines)


def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    start = r"(?<!\w)" if keyword[:1].isalnum() else ""
    end = r"(?!\w)" if keyword[-1:].isalnum() else ""
    return re.compile(start + re.escape(keyword.lower()) + end)


@lru_cache
def _type_patterns() -> tuple[
    tuple[dict[str, Any], tuple[tuple[str, re.Pattern[str], float], ...]], ...
]:
    result = []
    for entry in taxonomy.document_types():
        patterns = tuple(
            (
                kw,
                _keyword_pattern(kw),
                PHRASE_SPECIFICITY if " " in kw.strip() else WORD_SPECIFICITY,
            )
            for kw in entry["title_keywords"]
        )
        result.append((entry, patterns))
    return tuple(result)


def _confidence(best: float, second: float) -> float:
    strength = min(1.0, best / STRONG_SCORE)
    separation = (best - second) / best if best > 0 else 0.0
    value = BASE_CONFIDENCE + CONFIDENCE_RANGE * strength * (0.5 + 0.5 * separation)
    return round(min(value, 0.97), 2)


def _level(confidence: float) -> Level:
    return "high" if confidence >= HIGH else "medium" if confidence >= MEDIUM else "low"


def classify(pages: list[str], headings: list[str] | None = None) -> Classification:
    first_pages = normalize_whitespace(" ".join(pages[:CLASSIFY_PAGES])).lower()
    title_area = normalize_whitespace(pages[0] if pages else "").lower()[:TITLE_AREA_CHARS]
    first_page = normalize_whitespace(pages[0] if pages else "").lower()
    title_lines = _title_lines(pages[0] if pages else "")
    heading_text = " | ".join(h.lower() for h in headings or [])

    scores: dict[str, float] = {}
    reasons: dict[str, list[str]] = {}
    categories: dict[str, str] = {}
    secondary: dict[str, list[str]] = {}

    for entry, patterns in _type_patterns():
        type_id = entry["id"]
        categories[type_id] = entry["category"]
        secondary[type_id] = entry["secondary_categories"]
        for keyword, pattern, specificity in patterns:
            if pattern.search(title_lines):
                scores[type_id] = scores.get(type_id, 0) + TITLE_LINE_WEIGHT * specificity
                reasons.setdefault(type_id, []).append(f'title says "{keyword}"')
            elif pattern.search(title_area):
                scores[type_id] = scores.get(type_id, 0) + TITLE_WEIGHT * specificity
                reasons.setdefault(type_id, []).append(f'top of the document mentions "{keyword}"')
            elif pattern.search(first_page):
                scores[type_id] = scores.get(type_id, 0) + FIRST_PAGE_WEIGHT * specificity
                reasons.setdefault(type_id, []).append(f'first page mentions "{keyword}"')

    for rule, type_id, bonus, signal in STRUCTURE_RULES:
        if re.search(rule, first_pages):
            scores[type_id] = scores.get(type_id, 0) + bonus
            reasons.setdefault(type_id, []).append(signal)

    for words, type_ids, bonus, signal in HEADING_RULES:
        if sum(word in heading_text for word in words) >= 2:
            for type_id in type_ids:
                scores[type_id] = scores.get(type_id, 0) + bonus
                reasons.setdefault(type_id, []).append(signal)

    category_bonus: dict[str, float] = {}
    category_reasons: dict[str, list[str]] = {}
    for role_patterns, category, bonus, signal in ROLE_RULES:
        if all(re.search(p, first_pages) for p in role_patterns):
            category_bonus[category] = category_bonus.get(category, 0) + bonus
            category_reasons.setdefault(category, []).append(signal)

    final: dict[str, float] = {}
    for type_id, score in scores.items():
        bonus = CATEGORY_SHARE * category_bonus.get(categories[type_id], 0) + SECONDARY_SHARE * sum(
            category_bonus.get(c, 0) for c in secondary[type_id]
        )
        final[type_id] = score + bonus

    ranked = sorted(final.items(), key=lambda item: item[1], reverse=True)
    if not ranked or ranked[0][1] < MIN_SCORE:
        return _no_type(title_area, category_bonus, category_reasons)

    best_id, best = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    confidence = _confidence(best, second)
    level = _level(confidence)
    category = categories[best_id]
    signals = reasons.get(best_id, []) + category_reasons.get(category, [])
    runners_up = ranked[1 : MAX_ALTERNATIVES + 1]
    runner_total = sum(score for _, score in runners_up) or 1.0
    # Alternatives share what the top answer leaves over, in proportion to their scores.
    alternatives = [
        {"document_type": type_id, "confidence": round((1 - confidence) * score / runner_total, 2)}
        for type_id, score in runners_up
    ]
    if level == "low":
        # Never force a low-confidence answer: offer the best guesses instead.
        return Classification(
            category=category,
            document_type=None,
            confidence=confidence,
            confidence_level="low",
            status="needs_review",
            signals=signals,
            alternatives=[{"document_type": best_id, "confidence": confidence}, *alternatives][
                :MAX_ALTERNATIVES
            ],
        )
    return Classification(
        category, best_id, confidence, level, "confirmed", "rules", signals, alternatives
    )


def _no_type(
    title_area: str, category_bonus: dict[str, float], category_reasons: dict[str, list[str]]
) -> Classification:
    """No type is supported by the evidence: at most suggest a category, and ask the user."""
    if category_bonus:
        category = max(category_bonus, key=lambda c: category_bonus[c])
        signals = category_reasons[category]
    else:
        match = next(((p, c) for p, c in GENERIC_TITLE_WORDS if re.search(p, title_area)), None)
        if match is None:
            return Classification(
                None, None, 0.0, "low", "unknown", signals=["no recognisable title or structure"]
            )
        category = match[1]
        word = re.search(match[0], title_area)
        signals = [f'only a general title word was found ("{word.group(0) if word else ""}")']
    return Classification(
        category, None, GENERIC_CONFIDENCE, "low", "needs_review", signals=signals
    )


def user_verified(type_id: str) -> Classification:
    entry = taxonomy.document_type(type_id)
    if entry is None:
        raise ValueError(f"Unknown document type: {type_id}")
    return Classification(
        category=entry["category"],
        document_type=type_id,
        confidence=1.0,
        confidence_level="high",
        status="user_verified",
        method="user",
        signals=["chosen by the user"],
    )
