"""Phase 6: concept extraction — per-case checks plus precision / recall over the labelled set."""

import pytest

from app.services.extraction import detect_party_roles, extract_facts, strip_leading_clutter
from tests.extraction_cases import CASES, SCORED, ExtractionCase

MIN_PRECISION = 0.95
MIN_RECALL = 0.95


def _extract(case: ExtractionCase) -> set[tuple[str, str]]:
    return {(f.concept, f.value) for f in extract_facts([(case.chunk_index, case.text, None)])}


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.text[:50])
def test_extraction_case(case: ExtractionCase) -> None:
    found = _extract(case)
    assert case.expected <= found, f"missing {case.expected - found}"
    scored = {fact for fact in found if fact[0] in SCORED}
    assert scored <= case.expected, f"unexpected {scored - case.expected}"
    assert not {concept for concept, _ in found} & case.absent
    assert case.keywords <= {concept for concept, _ in found}


def test_precision_and_recall() -> None:
    true_positive = extracted = expected = 0
    for case in CASES:
        scored = {fact for fact in _extract(case) if fact[0] in SCORED}
        true_positive += len(scored & case.expected)
        extracted += len(scored)
        expected += len(case.expected)
    precision = true_positive / extracted
    recall = true_positive / expected
    assert precision >= MIN_PRECISION, precision
    assert recall >= MIN_RECALL, recall


def test_every_fact_keeps_exact_evidence_with_confidence() -> None:
    for case in CASES:
        for fact in extract_facts([(case.chunk_index, case.text, None)]):
            assert fact.source_text in case.text  # an exact piece of the document
            assert 0 < fact.confidence <= 1


def test_normalized_values() -> None:
    facts = {
        f.concept: f.normalized_value
        for f in extract_facts(
            [
                (5, "The Company shall pay a gross salary of INR 1,20,000 per month.", None),
                (5, "Interest at 18% per annum applies.", None),
                (5, "The first six (6) months of employment are a probation period.", None),
            ]
        )
    }
    assert facts["salary"] == {
        "kind": "money",
        "amount": 120000,
        "currency": "INR",
        "period": "per_month",
    }
    assert facts["interest_rate"] == {"kind": "percentage", "value": 18.0, "period": "per_year"}
    assert facts["probation"] == {"kind": "duration", "number": 6, "unit": "months"}


def test_leading_clutter_is_removed_but_evidence_stays_exact() -> None:
    raw = "Termination 12.1 Either party may terminate this Agreement by giving notice."
    cleaned = strip_leading_clutter(raw)
    assert cleaned.startswith("Either party")
    assert cleaned in raw
    assert strip_leading_clutter("12. Termination 12.1 Either party may terminate now.").startswith(
        "Either"
    )
    assert strip_leading_clutter("(1) A landlord shall give the tenant written notice.").startswith(
        "A landlord"
    )
    assert strip_leading_clutter("The fee is Rs. 1.5 lakh payable on signing the deed.").startswith(
        "The fee"
    )


def test_party_roles() -> None:
    text = (
        'This Agreement is made on 1 May 2026 between Ravi Kumar (the "Landlord") and '
        'Meera Nair (the "Tenant").'
    )
    assert detect_party_roles(text) == [("Ravi Kumar", "landlord"), ("Meera Nair", "tenant")]
