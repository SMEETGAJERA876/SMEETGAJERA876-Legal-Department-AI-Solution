"""Comparing a document against the official format for its kind (app/services/formats.py).

Two things to hold: the data file stays consistent with the taxonomy it keys off, and the
comparison reports a part as missing only when it really is absent — a false "missing" on a
legal document is worse than saying nothing, because it sends someone back to an official with
a complaint that is not true.
"""

import json
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.models import Document, DocumentPage
from app.services import formats, taxonomy

FORMATS_FILE = Path(__file__).resolve().parents[2] / "data" / "formats" / "document_formats.json"


def test_every_format_keys_off_a_real_document_type() -> None:
    known = taxonomy.document_type_ids()
    for fmt in formats.formats():
        assert fmt["document_type_ids"], fmt["id"]
        for type_id in fmt["document_type_ids"]:
            assert type_id in known, f'{fmt["id"]} names unknown document type {type_id}'


def test_each_format_is_complete_and_unambiguous() -> None:
    seen_format_ids: set[str] = set()
    claimed_types: set[str] = set()
    for fmt in formats.formats():
        assert fmt["id"] not in seen_format_ids, f'duplicate format id {fmt["id"]}'
        seen_format_ids.add(fmt["id"])
        for type_id in fmt["document_type_ids"]:
            # Two formats claiming one document type would make the result depend on file order.
            assert type_id not in claimed_types, f"{type_id} is claimed by two formats"
            claimed_types.add(type_id)
        assert fmt["authority"], fmt["id"]
        assert any(part["required"] for part in fmt["parts"]), f'{fmt["id"]} requires nothing'
        part_ids: set[str] = set()
        for part in fmt["parts"]:
            assert part["id"] not in part_ids, f'{fmt["id"]}: duplicate part {part["id"]}'
            part_ids.add(part["id"])
            assert part["label"] and part["why"], part["id"]
            assert part["patterns"], f'{part["id"]} can never be found'


def test_the_data_file_is_valid_json_with_a_version() -> None:
    data = json.loads(FORMATS_FILE.read_text(encoding="utf-8"))
    assert data["version"]
    assert data["description"]


@pytest.fixture
def document_with_pages(database: None):  # type: ignore[no-untyped-def]
    """Make a document out of given page texts, classified as a given type."""
    created: list[uuid.UUID] = []

    def make(type_id: str, pages: list[str]) -> uuid.UUID:
        with SessionLocal() as db:
            document = Document(
                original_filename="format_test.pdf",
                stored_filename=f"format-test-{uuid.uuid4().hex}.pdf",
                file_size=1,
                format="pdf",
                document_type_id=type_id,
                page_count=len(pages),
            )
            db.add(document)
            db.flush()
            for number, text in enumerate(pages, start=1):
                db.add(DocumentPage(document_id=document.id, page_number=number, text=text))
            db.commit()
            created.append(document.id)
            return document.id

    yield make
    with SessionLocal() as db:
        for document_id in created:
            document = db.get(Document, document_id)
            if document is not None:
                db.delete(document)
        db.commit()


def _status(result: formats.FormatResult, part_id: str) -> str:
    return next(p.status for p in result.parts if p.id == part_id)


def test_a_complete_agreement_reports_nothing_missing(document_with_pages) -> None:  # type: ignore[no-untyped-def]
    document_id = document_with_pages(
        "property.rental_agreement",
        [
            "RENT AGREEMENT. This agreement is made on 1 April 2026 between Ravi Kumar "
            "(Lessor) and Meera Nair (Lessee) on non-judicial stamp paper of Rs. 100.",
            "The premises described in the schedule are let for a term of eleven months "
            "commencing from 1 April 2026 at a monthly rent of Rs. 15,000 payable on or before "
            "the fifth day. A refundable security deposit of Rs. 90,000 is paid. Maintenance "
            "charges and electricity are payable by the tenant. The Lessee shall not sublet.",
            "Either party may terminate this agreement by giving two months notice. Registered "
            "before the Sub-Registrar. In witness whereof the parties have signed. "
            "Witness 1: A. Rao. Witness 2: S. Devi. Signature of Lessor. Signature of Lessee.",
        ],
    )
    with SessionLocal() as db:
        result = formats.check(db, document_id, "property.rental_agreement")
    assert result is not None
    assert result.missing_required == [], [p.label for p in result.missing_required]
    assert result.score == 1.0


def test_missing_and_unfilled_parts_are_told_apart(document_with_pages) -> None:  # type: ignore[no-untyped-def]
    document_id = document_with_pages(
        "property.rental_agreement",
        [
            "RENT AGREEMENT between Ravi Kumar (Lessor) and Meera Nair (Lessee), "
            "dated ____________. The premises are let at a monthly rent of Rs. 15,000 "
            "for a term of eleven months. Security deposit Rs. 90,000. Two months notice. "
            "Maintenance charges payable by the tenant. Signature of Lessor. Witness 1.",
        ],
    )
    with SessionLocal() as db:
        result = formats.check(db, document_id, "property.rental_agreement")
    assert result is not None
    # The date label is there, but the value after it was never filled in.
    assert _status(result, "date") == "empty"
    # Stamp duty is not mentioned at all.
    assert _status(result, "stamp") == "missing"
    assert _status(result, "rent") == "present"


def test_every_finding_can_be_checked_by_the_reader(document_with_pages) -> None:  # type: ignore[no-untyped-def]
    """A part reported present or empty must say where, so nobody has to take our word."""
    document_id = document_with_pages(
        "property.rental_agreement",
        ["Between Ravi Kumar (Lessor) and Meera Nair (Lessee). Monthly rent of Rs. 15,000."],
    )
    with SessionLocal() as db:
        result = formats.check(db, document_id, "property.rental_agreement")
    assert result is not None
    for part in result.parts:
        if part.status == "missing":
            assert part.page_number is None and part.evidence is None
        else:
            assert part.page_number is not None
            assert part.evidence, part.label


def test_a_type_we_do_not_describe_returns_nothing(document_with_pages) -> None:  # type: ignore[no-untyped-def]
    document_id = document_with_pages("legal.nda", ["A confidentiality agreement."])
    with SessionLocal() as db:
        assert formats.check(db, document_id, "legal.nda") is None
        assert formats.check(db, document_id, None) is None


def test_the_api_reports_the_comparison(client: TestClient, processed_document_id: str) -> None:
    body = client.get(f"/documents/{processed_document_id}/format-check").json()
    assert body["available"] is True
    assert body["format_name"] == "Employment agreement or appointment letter"
    assert body["required_total"] > 0
    assert 0.0 <= body["score"] <= 1.0
    labels = {p["id"]: p for p in body["parts"]}
    assert labels["salary"]["status"] == "present"
    assert labels["salary"]["page_number"]
    # The authority is shown so the checklist is not mistaken for our own opinion.
    assert "Code on Wages" in body["authority"]


def test_the_api_says_so_when_there_is_no_format(
    client: TestClient, processed_document_id: str, database: None
) -> None:
    with SessionLocal() as db:
        document = db.get(Document, uuid.UUID(processed_document_id))
        assert document is not None
        original = document.document_type_id
        document.document_type_id = "legal.nda"
        db.commit()
    try:
        body = client.get(f"/documents/{processed_document_id}/format-check").json()
        assert body["available"] is False
        assert body["covered_formats"], "the message should say what we can compare"
    finally:
        with SessionLocal() as db:
            document = db.get(Document, uuid.UUID(processed_document_id))
            assert document is not None
            document.document_type_id = original
            db.commit()


def test_the_api_simplifies_a_passage(client: TestClient, processed_document_id: str) -> None:
    body = client.post(
        f"/documents/{processed_document_id}/simplify",
        json={"text": "The Lessee shall pay the Lessor Rs. 15,000 prior to the fifth day."},
    ).json()
    assert body["changed"] is True
    assert body["worth_showing"] is True
    assert "before" in body["simple"]
    assert "Rs. 15,000" in body["simple"], "an amount must never be dropped"
    assert body["original"].startswith("The Lessee")
    assert {"legal": "lessee", "plain": "tenant"} in body["terms"]


def test_simplify_rejects_an_empty_request(client: TestClient, processed_document_id: str) -> None:
    response = client.post(f"/documents/{processed_document_id}/simplify", json={"text": ""})
    assert response.status_code == 422
