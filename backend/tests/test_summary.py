"""The one-file PDF summary: key dates, notices, deadlines, money, review items, questions."""

import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.services.summary_pdf import _clean_quote
from tests.test_document_check import upload


def summary_text(client: TestClient, document_id: str) -> tuple[str, dict[str, str]]:
    response = client.get(f"/documents/{document_id}/summary")
    assert response.status_code == 200, response.text
    assert response.content.startswith(b"%PDF-")
    with pymupdf.open(stream=response.content, filetype="pdf") as pdf:
        text = " ".join(" ".join(page.get_text().split()) for page in pdf)
    return text, dict(response.headers)


@pytest.fixture(scope="module")
def employment_summary(database: None, client: TestClient) -> tuple[str, dict[str, str]]:
    return summary_text(client, upload(client, "employment_agreement.pdf"))


def test_summary_is_a_downloadable_pdf(employment_summary: tuple[str, dict[str, str]]) -> None:
    _, headers = employment_summary
    assert headers["content-type"] == "application/pdf"
    assert headers["content-disposition"].startswith("attachment")
    assert "employment_agreement%20-%20summary.pdf" in headers["content-disposition"]


def test_summary_lists_key_facts_with_pages(employment_summary: tuple[str, dict[str, str]]) -> None:
    text, _ = employment_summary
    for expected in [
        "DOCUMENT SUMMARY",
        "employment agreement",
        "Northwind Analytics Private Limited and Priya Sharma",
        "At a glance",
        "Notice period 14 days (p. 2); 90 days (p. 7)",
        "Dates, notice periods and deadlines",
        "Money, fees and penalties",
        "INR 1,20,000",
        "Page 7 Clause 12.1",
        "Questions to ask a legal professional",
        "not legal advice",
    ]:
        assert expected in text, expected
    assert "Needs your attention" not in text  # a clean document has nothing to review


def test_summary_includes_items_to_review(database: None, client: TestClient) -> None:
    text, _ = summary_text(client, upload(client, "rental_agreement_with_mistakes.pdf"))
    assert "Needs your attention" in text
    assert "Refers to a clause that doesn't exist: Clause 9" in text
    assert "ninety (60)" in text


def test_government_notice_summary(database: None, client: TestClient) -> None:
    text, _ = summary_text(client, upload(client, "government_public_notice.pdf"))
    assert "on or before 30 April 2026 (p. 3)" in text
    assert "Rs. 250" in text
    assert "Important notes" in text


def test_quote_cleanup_removes_headings_and_numbers() -> None:
    assert _clean_quote("Termination 12.1 Either party may terminate this Agreement").startswith(
        "Either party"
    )
    assert _clean_quote("Rule 5. Notice to vacate (1) A landlord shall give notice").startswith(
        "A landlord"
    )
