"""Scanned documents: pages without a text layer are read with OCR (parsing/ocr.py)."""

import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.services.parsing import parse_file

SCAN_DPI = 150
SCANNED_PAGES = 2


def scanned_copy(pdf: bytes, pages: int = SCANNED_PAGES) -> bytes:
    """An image-only PDF, like a scanner produces: each page is just a picture of the page."""
    with pymupdf.open(stream=pdf, filetype="pdf") as source, pymupdf.open() as scan:
        for index in range(min(pages, source.page_count)):
            pixmap = source[index].get_pixmap(dpi=SCAN_DPI)
            page = scan.new_page(width=source[index].rect.width, height=source[index].rect.height)
            page.insert_image(page.rect, pixmap=pixmap)
        return scan.tobytes()


@pytest.fixture(scope="module")
def scanned_pdf(sample_pdf: bytes) -> bytes:
    data = scanned_copy(sample_pdf)
    with pymupdf.open(stream=data, filetype="pdf") as check:
        assert not check[0].get_text().strip(), "the copy must have no text layer"
    return data


def test_scanned_pages_are_read_with_ocr(scanned_pdf: bytes) -> None:
    parsed = parse_file(scanned_pdf, "pdf")
    assert all(p.ocr and not p.has_text_layer for p in parsed.pages)
    text = " ".join(parsed.page_texts)
    assert "EMPLOYMENT AGREEMENT" in text
    assert "Northwind Analytics" in text
    assert any("OCR" in w for w in parsed.warnings)
    # Blocks carry positions in PDF points, inside the page.
    first = parsed.pages[0]
    assert first.blocks and all(
        0 <= b.bbox[0] < b.bbox[2] <= first.width + 1 for b in first.blocks if b.bbox
    )


def test_ocr_can_be_skipped(scanned_pdf: bytes) -> None:
    with pytest.raises(Exception, match="Unable to read any text"):
        parse_file(scanned_pdf, "pdf", ocr=False)


def test_scanned_document_can_be_asked_about(
    database: None, client: TestClient, scanned_pdf: bytes
) -> None:
    response = client.post(
        "/documents", files={"file": ("scanned_agreement.pdf", scanned_pdf, "application/pdf")}
    )
    assert response.status_code == 201, response.text
    document_id = response.json()["id"]
    document = client.get(f"/documents/{document_id}").json()
    assert document["status"] == "ready", document
    answer = client.post(
        f"/documents/{document_id}/ask", json={"question": "Who is the employee?"}
    ).json()
    assert answer["found"], answer
    assert answer["citations"][0]["page_number"] in (1, 2)
    client.delete(f"/documents/{document_id}")
