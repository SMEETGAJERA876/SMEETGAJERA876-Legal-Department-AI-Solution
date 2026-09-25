"""Turn fact values as written ("ninety (90) days", "INR 1,20,000", "30 April 2026") into
machine-readable values (legal_fact.schema.json → normalized_value). Returns None when a value
can't be parsed with certainty — never guesses."""

import re
from datetime import date, datetime
from typing import Any

_DURATION = re.compile(r"(\d+)\s+(hour|day|week|month|year)s?\b", re.IGNORECASE)
_ORDINAL = re.compile(r"(\d{1,2})(?:st|nd|rd|th)\b", re.IGNORECASE)
_DATE_FORMATS = (
    "%B %d, %Y",
    "%B %d %Y",
    "%d %B %Y",
    "%d %B, %Y",
    "%b %d, %Y",
    "%b %d %Y",
    "%d %b %Y",
    "%d %b, %Y",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
)  # fmt: skip — dd/mm/yyyy first: the target market is India
_CURRENCIES = [
    (re.compile(r"US\$|USD|\$|dollars?", re.IGNORECASE), "USD"),
    (re.compile(r"₹|Rs\.?|INR|rupees?", re.IGNORECASE), "INR"),
    (re.compile(r"€|EUR|euros?", re.IGNORECASE), "EUR"),
    (re.compile(r"£|GBP|pounds?", re.IGNORECASE), "GBP"),
]
_AMOUNT = re.compile(r"\d[\d,]*(?:\.\d+)?")
_MULTIPLIERS = {"lakh": 100_000, "lakhs": 100_000, "crore": 10_000_000, "crores": 10_000_000,
                "million": 1_000_000}  # fmt: skip
_PERIODS = [
    (re.compile(r"per\s+month|a\s+month|monthly|each\s+month", re.IGNORECASE), "per_month"),
    (re.compile(r"per\s+(?:annum|year)|annual|yearly|p\.a\.", re.IGNORECASE), "per_year"),
    (re.compile(r"per\s+week|weekly", re.IGNORECASE), "per_week"),
    (re.compile(r"per\s+day|daily", re.IGNORECASE), "per_day"),
]
_DATE_QUALIFIERS = [
    ("on or before", "on_or_before"), ("not later than", "on_or_before"),
    ("no later than", "on_or_before"), ("last date", "on_or_before"), ("due", "on_or_before"),
    ("by", "on_or_before"), ("before", "before"), ("until", "until"), ("till", "until"),
]  # fmt: skip


def parse_date(text: str) -> date | None:
    cleaned = _ORDINAL.sub(r"\1", text.strip().rstrip(".")).replace("day of ", "")
    cleaned = re.sub(r"\s+", " ", cleaned).replace("Sept ", "Sep ")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def duration(value: str) -> dict[str, Any] | None:
    match = _DURATION.search(value)
    if not match:
        return None
    result: dict[str, Any] = {
        "kind": "duration",
        "number": int(match.group(1)),
        "unit": match.group(2).lower() + "s",
    }
    lowered = value.lower()
    if lowered.startswith("within"):
        result["qualifier"] = "within"
    elif lowered.startswith(("no later than", "not later than")):
        result["qualifier"] = "at_most"
    elif lowered.endswith("before"):
        result["qualifier"] = "before"
    elif "from the date" in lowered:
        result["qualifier"] = "after"
    return result


def date_value(value: str) -> dict[str, Any] | None:
    lowered = value.lower()
    qualifier = None
    remainder = value
    for lead, name in _DATE_QUALIFIERS:
        if lowered.startswith(lead + " "):
            qualifier, remainder = name, value[len(lead) + 1 :]
            break
    parsed = parse_date(remainder)
    if parsed is None:
        return None
    result: dict[str, Any] = {"kind": "date", "date": parsed.isoformat()}
    if qualifier:
        result["qualifier"] = qualifier
    return result


def money(value: str, sentence: str = "") -> dict[str, Any] | None:
    currency = next((code for pattern, code in _CURRENCIES if pattern.search(value)), None)
    amount_match = _AMOUNT.search(value)
    if currency is None or amount_match is None:
        return None
    amount = float(amount_match.group(0).replace(",", ""))
    unit = re.search(r"\b(lakhs?|crores?|million)\b", value, re.IGNORECASE)
    if unit:
        amount *= _MULTIPLIERS[unit.group(1).lower()]
    result: dict[str, Any] = {
        "kind": "money",
        "amount": int(amount) if amount.is_integer() else amount,
        "currency": currency,
    }
    period = next((name for pattern, name in _PERIODS if pattern.search(sentence)), None)
    if period:
        result["period"] = period
    return result


_PERCENT = re.compile(r"(\d{1,2}(?:\.\d{1,2})?)\s*%")
DURATION_CONCEPTS = {"notice_period", "duration", "probation", "cure_period", "leave"}
MONEY_CONCEPTS = {"payment", "salary", "rent", "deposit", "late_fee"}
DATE_CONCEPTS = {"important_dates", "effective_date"}


def percentage(value: str) -> dict[str, Any] | None:
    match = _PERCENT.search(value)
    if not match:
        return None
    result: dict[str, Any] = {"kind": "percentage", "value": float(match.group(1))}
    period = next((name for pattern, name in _PERIODS if pattern.search(value)), None)
    if period in ("per_month", "per_year"):
        result["period"] = period
    return result


def normalize(engine_key: str, value: str, source_text: str) -> dict[str, Any] | None:
    """Normalized value for a fact extracted by the engine, or None."""
    if engine_key in DURATION_CONCEPTS:
        return duration(value)
    if engine_key == "time_limits":
        return date_value(value) or duration(value)
    if engine_key in DATE_CONCEPTS:
        return date_value(value)
    if engine_key in MONEY_CONCEPTS:
        return money(value, source_text)
    if engine_key == "interest_rate":
        return percentage(value)
    return None
