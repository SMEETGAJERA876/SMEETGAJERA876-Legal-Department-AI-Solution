"""Phase 5: document classification — accuracy, calibration, never forcing, user verification."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.services import taxonomy
from app.services.classification import classify, user_verified
from tests.classification_cases import CASES, ClassificationCase
from tests.test_document_check import upload


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
def test_classification_case(case: ClassificationCase) -> None:
    result = classify([case.text], list(case.headings))
    assert result.document_type == case.expected, (result.to_json(), case.name)
    if case.expected_category:
        assert result.category == case.expected_category
    if case.expected is None:
        # never forced: no type, low confidence, and the user is asked (or it is unknown)
        assert result.confidence_level == "low"
        assert result.status in ("needs_review", "unknown")
    else:
        assert result.document_type in taxonomy.document_type_ids()
        assert result.status == "confirmed"
        assert result.signals, "a classification must explain itself"


def test_high_confidence_is_always_right() -> None:
    """Calibration: of the answers labelled 'high', all must be correct on the evaluation set."""
    high = [(c, classify([c.text], list(c.headings))) for c in CASES]
    high = [(c, r) for c, r in high if r.confidence_level == "high"]
    assert len(high) >= len(CASES) // 2
    assert all(r.document_type == c.expected for c, r in high)


def test_low_confidence_never_names_a_type() -> None:
    for case in CASES:
        result = classify([case.text], list(case.headings))
        if result.confidence_level == "low":
            assert result.document_type is None


def test_alternatives_are_valid_probabilities() -> None:
    result = classify([CASES[0].text], list(CASES[0].headings))
    for alternative in result.alternatives:
        assert 0 <= alternative["confidence"] <= 1
        assert alternative["document_type"] in taxonomy.document_type_ids()
    assert result.confidence + sum(a["confidence"] for a in result.alternatives) <= 1.01


def test_user_verified_rejects_unknown_types() -> None:
    with pytest.raises(ValueError):
        user_verified("not.a_type")
    result = user_verified("court.judgment")
    assert (result.category, result.status, result.method) == ("court", "user_verified", "user")


# ---------------------------------------------------------------- API


@pytest.fixture(scope="module")
def document_id(database: None, client: TestClient) -> str:
    return upload(client, "rental_agreement_with_mistakes.pdf")


def test_processing_stores_the_classification(client: TestClient, document_id: str) -> None:
    document = client.get(f"/documents/{document_id}").json()
    assert document["document_type_id"] == "property.rental_agreement"
    assert document["document_type"] == "Rental Agreement"
    assert document["category"] == "property"
    classification: dict[str, Any] = document["classification"]
    assert classification["status"] == "confirmed"
    assert any("rental agreement" in s for s in classification["signals"])


def test_types_endpoint_lists_the_taxonomy(client: TestClient, database: None) -> None:
    types = client.get("/documents/types").json()
    ids = {t["id"] for t in types}
    assert {"court.judgment", "government.circular", "legal.nda"} <= ids
    assert "other.unknown" not in ids
    judgment = next(t for t in types if t["id"] == "court.judgment")
    assert judgment["category_name"] == "Court / Judicial"


def test_user_can_correct_the_type(client: TestClient, document_id: str) -> None:
    response = client.put(
        f"/documents/{document_id}/classification",
        json={"document_type_id": "property.lease_agreement"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["document_type_id"] == "property.lease_agreement"
    assert body["document_type"] == "Lease Agreement"
    assert body["classification"]["status"] == "user_verified"
    # the automatic guess is kept as an alternative for transparency
    assert body["classification"]["alternatives"][0]["document_type"] == "property.rental_agreement"

    normalized = client.get(f"/documents/{document_id}/normalized").json()
    assert normalized["document"]["classification"]["status"] == "user_verified"


def test_user_cannot_pick_a_type_that_does_not_exist(client: TestClient, document_id: str) -> None:
    response = client.put(
        f"/documents/{document_id}/classification", json={"document_type_id": "legal.banana"}
    )
    assert response.status_code == 400
    assert response.json()["error"] == "unknown_document_type"
