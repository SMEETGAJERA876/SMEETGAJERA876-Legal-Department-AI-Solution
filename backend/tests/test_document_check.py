"""Document check (mistakes with page + suggestion) and auto-repair into a corrected copy."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.services.document_check import words_to_number

SAMPLES_DIR = Path(__file__).resolve().parents[2] / "samples"
MISTAKES_PDF = "rental_agreement_with_mistakes.pdf"
CLEAN_PDFS = ["employment_agreement.pdf", "government_public_notice.pdf", "tenancy_rules.pdf"]

EXPECTED = {
    ("repeated_word", 1, "the the"),
    ("blank_field", 1, "______"),
    ("spelling", 2, "tenent"),
    ("spelling", 2, "agrement"),
    ("number_mismatch", 3, "ninety (60)"),
    ("numbering_gap", 3, "6."),
    ("missing_reference", 3, "Clause 9"),
    ("unclosed_bracket", 3, "(including the roof."),
    ("blank_field", 4, "________"),
}


def upload(client: TestClient, filename: str) -> str:
    if not (SAMPLES_DIR / filename).exists():
        from scripts.make_sample_pdf import build_all_samples

        build_all_samples()
    content = (SAMPLES_DIR / filename).read_bytes()
    response = client.post("/documents", files={"file": (filename, content, "application/pdf")})
    assert response.status_code == 201, response.text
    document_id: str = response.json()["id"]
    assert client.get(f"/documents/{document_id}").json()["status"] == "ready"
    return document_id


@pytest.fixture(scope="module")
def mistakes_id(database: None, client: TestClient) -> str:
    return upload(client, MISTAKES_PDF)


def test_words_to_number() -> None:
    assert words_to_number("ninety") == 90
    assert words_to_number("forty-five") == 45
    assert words_to_number("one hundred and twenty") == 120
    assert words_to_number("banana") is None


def test_finds_every_mistake_with_page_and_suggestion(client: TestClient, mistakes_id: str) -> None:
    body = client.get(f"/documents/{mistakes_id}/issues").json()
    found = {(i["kind"], i["page_number"], i["original"]) for i in body["issues"]}
    assert found == EXPECTED
    suggestions = {i["original"]: i["suggestion"] for i in body["issues"] if i["fixable"]}
    assert suggestions == {"the the": "the", "tenent": "tenant", "agrement": "agreement"}
    assert body["fixable_count"] == 3
    assert body["review_count"] == 6


@pytest.mark.parametrize("filename", CLEAN_PDFS)
def test_clean_documents_have_no_false_alarms(
    database: None, client: TestClient, filename: str
) -> None:
    document_id = upload(client, filename)
    assert client.get(f"/documents/{document_id}/issues").json()["issues"] == []


def test_repair_creates_corrected_copy_and_keeps_original(
    client: TestClient, mistakes_id: str
) -> None:
    issues = client.get(f"/documents/{mistakes_id}/issues").json()["issues"]
    original_pdf = client.get(f"/documents/{mistakes_id}/file").content

    response = client.post(
        f"/documents/{mistakes_id}/repair", json={"issue_ids": [i["id"] for i in issues]}
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert {i["original"] for i in body["applied"]} == {"the the", "tenent", "agrement"}
    assert len(body["not_applied"]) == 6  # review items are never changed automatically
    corrected = body["document"]
    assert corrected["original_filename"] == "rental_agreement_with_mistakes (corrected).pdf"
    assert corrected["source_document_id"] == mistakes_id
    assert {c["replacement"] for c in corrected["changes"]} == {"the", "tenant", "agreement"}

    # the corrected copy is processed like any upload and the fixed mistakes are gone
    assert client.get(f"/documents/{corrected['id']}").json()["status"] == "ready"
    remaining = client.get(f"/documents/{corrected['id']}/issues").json()
    assert remaining["fixable_count"] == 0
    assert remaining["review_count"] == 6
    search = client.get(
        f"/documents/{corrected['id']}/search", params={"q": "tenant moves in", "mode": "exact"}
    ).json()
    assert search["results"][0]["page_number"] == 2

    # the original is untouched
    assert client.get(f"/documents/{mistakes_id}/file").content == original_pdf
    assert len(client.get(f"/documents/{mistakes_id}/issues").json()["issues"]) == 9

    download = client.get(f"/documents/{corrected['id']}/file", params={"download": "true"})
    assert download.headers["content-type"] == "application/pdf"
    assert download.headers["content-disposition"].startswith("attachment")
    assert "corrected" in download.headers["content-disposition"]


def test_repair_refuses_review_only_items(client: TestClient, mistakes_id: str) -> None:
    issues = client.get(f"/documents/{mistakes_id}/issues").json()["issues"]
    review_ids = [i["id"] for i in issues if not i["fixable"]]
    response = client.post(f"/documents/{mistakes_id}/repair", json={"issue_ids": review_ids})
    assert response.status_code == 400
    assert response.json()["error"] == "nothing_to_fix"


def test_repair_rejects_unknown_issue_ids(client: TestClient, mistakes_id: str) -> None:
    response = client.post(f"/documents/{mistakes_id}/repair", json={"issue_ids": ["nope"]})
    assert response.status_code == 400
    assert response.json()["error"] == "issues_changed"
