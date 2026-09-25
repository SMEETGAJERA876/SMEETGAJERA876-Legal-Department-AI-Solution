"""End-to-end API tests: upload → process → overview → search → ask → questions."""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.usefixtures("database")


def test_upload_rejects_unrecognised_content_even_if_named_pdf(client: TestClient) -> None:
    response = client.post(
        "/documents", files={"file": ("notes.pdf", b"hello, not a pdf", "application/pdf")}
    )
    assert response.status_code == 415
    assert response.json()["error"] == "unsupported_file_type"
    assert "isn't recognised" in response.json()["message"]


def _docx_bytes() -> bytes:
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<w:document/>")
    return buffer.getvalue()


@pytest.mark.parametrize(
    ("filename", "content", "label"),
    [
        ("contract.docx", _docx_bytes(), "Word (DOCX)"),
        ("notice.png", b"\x89PNG\r\n\x1a\n" + b"\0" * 32, "PNG image"),
        ("order.jpg", b"\xff\xd8\xff\xe0" + b"\0" * 32, "JPEG image"),
    ],
)
def test_upload_explains_formats_not_supported_yet(
    client: TestClient, filename: str, content: bytes, label: str
) -> None:
    response = client.post(
        "/documents", files={"file": (filename, content, "application/octet-stream")}
    )
    assert response.status_code == 415
    assert response.json()["message"].startswith(f"{label} files are not supported yet")


def test_format_comes_from_content_not_declared_type(client: TestClient, sample_pdf: bytes) -> None:
    response = client.post("/documents", files={"file": ("a.txt", sample_pdf, "text/plain")})
    assert response.status_code == 201
    assert response.json()["format"] == "pdf"


def test_unreadable_pdf_fails_with_explanation(client: TestClient) -> None:
    response = client.post(
        "/documents", files={"file": ("broken.pdf", b"%PDF-1.4 garbage", "application/pdf")}
    )
    assert response.status_code == 201
    document = client.get(f"/documents/{response.json()['id']}").json()
    assert document["status"] == "failed"
    assert document["error_message"]


def test_processing_preserves_every_page(client: TestClient, processed_document_id: str) -> None:
    document = client.get(f"/documents/{processed_document_id}").json()
    assert document["page_count"] == 10
    assert document["document_type"] == "Employment Agreement"
    assert document["document_type_id"] == "employment.employment_agreement"
    assert document["category"] == "employment"
    assert document["classification"]["confidence_level"] == "high"
    assert document["parties"] == ["Northwind Analytics Private Limited", "Priya Sharma"]


def test_file_is_served_as_pdf(client: TestClient, processed_document_id: str) -> None:
    response = client.get(f"/documents/{processed_document_id}/file")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")


def test_overview_has_sourced_notice_period(client: TestClient, processed_document_id: str) -> None:
    overview = client.get(f"/documents/{processed_document_id}/overview").json()
    notice = next(c for c in overview["concepts"] if c["concept"] == "notice_period")
    ninety = next(f for f in notice["facts"] if f["value"] == "90 days")
    assert ninety["source"]["page_number"] == 7
    assert ninety["source"]["clause_ref"] == "12.1"
    assert overview["counts"]["pages"] == 10


def test_exact_search_finds_word_with_page(client: TestClient, processed_document_id: str) -> None:
    body = client.get(
        f"/documents/{processed_document_id}/search", params={"q": "notice", "mode": "exact"}
    ).json()
    pages = {r["page_number"] for r in body["results"]}
    assert 7 in pages
    assert all("notice" in r["snippet"].lower() for r in body["results"])


def test_exact_search_treats_wildcards_literally(
    client: TestClient, processed_document_id: str
) -> None:
    body = client.get(
        f"/documents/{processed_document_id}/search", params={"q": "%", "mode": "exact"}
    ).json()
    assert body["results"] == []


def test_semantic_search_understands_meaning(
    client: TestClient, processed_document_id: str
) -> None:
    body = client.get(
        f"/documents/{processed_document_id}/search",
        params={"q": "What notice do I need before leaving?", "mode": "semantic"},
    ).json()
    top = body["results"][0]
    assert top["page_number"] == 7
    assert "ninety (90) days written" in top["snippet"]


def test_ask_returns_cited_answer(client: TestClient, processed_document_id: str) -> None:
    body = client.post(
        f"/documents/{processed_document_id}/ask", json={"question": "What is my notice period?"}
    ).json()
    assert body["found"] is True
    assert "90 days" in body["answer"]
    assert body["citations"][0]["page_number"] == 7

    follow_up = client.post(
        f"/documents/{processed_document_id}/ask",
        json={
            "question": "What happens if I leave early?",
            "conversation_id": body["conversation_id"],
        },
    ).json()
    assert follow_up["conversation_id"] == body["conversation_id"]
    assert follow_up["citations"]
    assert {c["page_number"] for c in follow_up["citations"]} & {7, 8}  # termination/penalty
    assert follow_up["related_concepts"]


def test_ask_admits_when_document_has_no_answer(
    client: TestClient, processed_document_id: str
) -> None:
    body = client.post(
        f"/documents/{processed_document_id}/ask",
        json={"question": "What is the recipe for chocolate cake?"},
    ).json()
    assert body["found"] is False
    assert body["citations"] == []
    assert "couldn't find" in body["answer"]


def test_professional_questions_have_sources(
    client: TestClient, processed_document_id: str
) -> None:
    body = client.get(f"/documents/{processed_document_id}/questions").json()
    assert "legal professional" in body["intro"]
    assert any("90 days" in q["question"] for q in body["questions"])
    assert all(q["source"]["page_number"] >= 1 for q in body["questions"])


def test_missing_document_returns_friendly_404(client: TestClient) -> None:
    response = client.get("/documents/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"
