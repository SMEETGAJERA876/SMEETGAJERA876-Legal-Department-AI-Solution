"""Phase 3: parser interface, format detection and the normalized document output."""

import io
import zipfile
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from referencing import Registry

from app.services.parsing import DocumentParseError, detect_format, get_parser
from app.services.parsing.pdf import PDFParser
from tests.test_document_check import SAMPLES_DIR, upload
from tests.test_taxonomy_data import errors, registry  # noqa: F401  (fixture)

SAMPLES = [
    "employment_agreement.pdf",
    "government_public_notice.pdf",
    "tenancy_rules.pdf",
    "rental_agreement_with_mistakes.pdf",
]


# ---------------------------------------------------------------- format detection & parsers


def test_detect_format_from_content() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", "<w:document/>")
    docx = buffer.getvalue()
    assert detect_format(b"%PDF-1.7") == "pdf"
    assert detect_format(docx[:8], docx) == "docx"
    assert detect_format(b"\x89PNG\r\n\x1a\n") == "png"
    assert detect_format(b"\xff\xd8\xff\xe0") == "jpg"
    assert detect_format(b"II*\x00") == "tiff"
    assert detect_format(b"hello") is None


def test_unsupported_format_has_a_friendly_message() -> None:
    with pytest.raises(DocumentParseError, match="Word \\(DOCX\\) files are not supported yet"):
        get_parser("docx")
    assert get_parser("pdf").name == "PDFParser"


def test_pdf_parser_returns_pages_and_positioned_blocks() -> None:
    parsed = PDFParser().parse(SAMPLES_DIR / "employment_agreement.pdf")
    assert parsed.format == "pdf"
    assert len(parsed.pages) == 10
    assert not parsed.is_scanned
    page7 = parsed.pages[6]
    assert "ninety (90) days written notice" in page7.text
    headings = [b.text for b in page7.blocks if b.type == "heading"]
    assert "12. Termination" in headings
    assert any(b.type == "footer" and b.text == "Page 7 of 10" for b in page7.blocks)
    assert all(b.bbox is not None and b.bbox[2] > b.bbox[0] for b in page7.blocks)


# ---------------------------------------------------------------- normalized output


@pytest.fixture(scope="module")
def normalized(database: None, client: TestClient) -> dict[str, dict[str, Any]]:
    result = {}
    for filename in SAMPLES:
        document_id = upload(client, filename)
        response = client.get(f"/documents/{document_id}/normalized")
        assert response.status_code == 200, response.text
        result[filename] = response.json()
    return result


@pytest.mark.parametrize("filename", SAMPLES)
def test_normalized_output_matches_schema_and_evidence(
    filename: str,
    normalized: dict[str, dict[str, Any]],
    registry: Registry,  # noqa: F811
) -> None:
    doc = normalized[filename]
    assert errors("normalized_document", doc, registry) == []
    pages = {p["page_number"]: p["text"] for p in doc["pages"]}
    located = 0
    for fact in doc["facts"]:
        evidence = fact["evidence"]
        if "char_start" in evidence:
            located += 1
            text = pages[evidence["page_number"]]
            assert text[evidence["char_start"] : evidence["char_end"]] == evidence["source_text"]
    assert located == len(doc["facts"]), "every fact should point at its exact text"
    clauses = [c for s in doc["sections"] for c in s["clauses"]]
    assert clauses
    for clause in clauses:
        if "char_start" in clause:
            text = pages[clause["page_number"]]
            assert text[clause["char_start"] : clause["char_end"]] == clause["text"]
    assert sum("char_start" in c for c in clauses) >= 0.9 * len(clauses)
    assert doc["processing"]["parser"] == "PDFParser"
    assert doc["document"]["format"] == "pdf"


def _fact(doc: dict[str, Any], concept: str, value: str) -> dict[str, Any]:
    return next(f for f in doc["facts"] if f["concept"] == concept and f["value"] == value)


def test_employment_agreement_normalized(normalized: dict[str, dict[str, Any]]) -> None:
    doc = normalized["employment_agreement.pdf"]
    assert doc["document"]["classification"]["document_type"] == "employment.employment_agreement"
    assert doc["document"]["classification"]["confidence_level"] == "high"
    notice = _fact(doc, "contract.notice_period", "90 days")
    assert notice["normalized_value"] == {"kind": "duration", "number": 90, "unit": "days"}
    assert notice["evidence"]["page_number"] == 7
    assert notice["evidence"]["clause_number"] == "12.1"
    assert notice["evidence"]["section"] == "Termination"
    salary = _fact(doc, "employment.salary", "INR 1,20,000")
    assert salary["normalized_value"] == {
        "kind": "money", "amount": 120000, "currency": "INR", "period": "per_month",
    }  # fmt: skip
    termination = next(s for s in doc["sections"] if s.get("number") == "12")
    assert termination["heading"] == "Termination"
    assert termination["role"] == "termination"
    clause = termination["clauses"][0]
    assert "contract.notice_period" in clause["concepts"]
    assert notice["id"] in clause["fact_ids"]


def test_government_notice_normalized(normalized: dict[str, dict[str, Any]]) -> None:
    doc = normalized["government_public_notice.pdf"]
    assert doc["document"]["classification"]["document_type"] == "public_notice.public_notice"
    deadline = _fact(doc, "government.deadline", "on or before 30 April 2026")
    assert deadline["normalized_value"] == {
        "kind": "date", "date": "2026-04-30", "qualifier": "on_or_before",
    }  # fmt: skip
    within = _fact(doc, "government.deadline", "within 15 days")
    assert within["normalized_value"]["qualifier"] == "within"


def test_rules_document_keeps_rule_numbers(normalized: dict[str, dict[str, Any]]) -> None:
    doc = normalized["tenancy_rules.pdf"]
    assert doc["document"]["classification"]["document_type"] == "policy.rules"
    numbers = {s.get("number") for s in doc["sections"]}
    assert {"Rule 5", "Rule 6", "Chapter II"} <= numbers
    rule5 = next(s for s in doc["sections"] if s.get("number") == "Rule 5")
    assert [c["clause_number"] for c in rule5["clauses"]] == ["Rule 5(1)", "Rule 5(2)"]


def test_normalized_requires_processed_document(client: TestClient, database: None) -> None:
    response = client.get("/documents/00000000-0000-0000-0000-000000000000/normalized")
    assert response.status_code == 404


def test_samples_exist() -> None:
    for filename in SAMPLES:
        assert (Path(SAMPLES_DIR) / filename).exists()
