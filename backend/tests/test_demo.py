"""The public read-only demo (docs/Demo.md).

Two things have to hold at once: a visitor who never signs in can use a demo document fully,
and nothing about that weakens the privacy of everybody else's documents.
"""

import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import auth
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import Document
from tests.conftest import bearer


@pytest.fixture
def demo_document_id(
    database: None, client: TestClient, sample_pdf: bytes, firebase_mode: None
) -> Iterator[str]:
    """Upload a document as Alice, then flag it as a demo document the way seed_demo does."""
    response = client.post(
        "/documents",
        headers=bearer("token-alice"),
        files={"file": ("demo_agreement.pdf", sample_pdf, "application/pdf")},
    )
    assert response.status_code == 201, response.text
    document_id = response.json()["id"]
    with SessionLocal() as db:
        document = db.get(Document, uuid.UUID(document_id))
        assert document is not None
        document.user_id = auth.get_demo_user(db).id
        document.is_demo = True
        db.commit()
    yield document_id
    with SessionLocal() as db:
        document = db.get(Document, uuid.UUID(document_id))
        if document is not None:
            db.delete(document)
            db.commit()


def test_demo_document_is_fully_usable_without_signing_in(
    client: TestClient, demo_document_id: str, firebase_mode: None
) -> None:
    base = f"/documents/{demo_document_id}"
    for path in (
        base,
        f"{base}/file",
        f"{base}/overview",
        f"{base}/normalized",
        f"{base}/questions",
        f"{base}/issues",
        f"{base}/summary",
        f"{base}/search?q=notice",
        f"{base}/search?q=notice&mode=semantic",
    ):
        assert client.get(path).status_code == 200, path

    answer = client.post(f"{base}/ask", json={"question": "What is my notice period?"})
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["found"] is True
    assert body["citations"], "a demo answer must still carry its sources"


def test_demo_document_is_read_only_for_everyone(
    client: TestClient, demo_document_id: str, firebase_mode: None
) -> None:
    base = f"/documents/{demo_document_id}"
    writes: list[tuple[str, str, dict[str, Any] | None]] = [
        ("DELETE", base, None),
        ("PUT", f"{base}/classification", {"document_type_id": "legal.nda"}),
        ("POST", f"{base}/repair", {"issue_ids": ["x"]}),
    ]
    # Anonymous and signed in alike: the demo documents belong to the deployment.
    for headers in ({}, bearer("token-alice")):
        for method, path, payload in writes:
            response = client.request(method, path, json=payload, headers=headers)
            assert response.status_code == 403, f"{method} {path} {headers}"
            assert response.json()["error"] == "demo_read_only"


def test_demo_listing_describes_each_document(
    client: TestClient, demo_document_id: str
) -> None:
    body = client.get("/demo").json()
    assert body["enabled"] is True
    listed = {d["id"]: d for d in body["documents"]}
    assert demo_document_id in listed
    assert listed[demo_document_id]["page_count"]


def test_ordinary_documents_stay_private(
    client: TestClient, sample_pdf: bytes, firebase_mode: None
) -> None:
    """The demo must not open a door to anyone else's upload."""
    response = client.post(
        "/documents",
        headers=bearer("token-bob"),
        files={"file": ("bob_private.pdf", sample_pdf, "application/pdf")},
    )
    document_id = response.json()["id"]
    base = f"/documents/{document_id}"
    for path in (base, f"{base}/file", f"{base}/overview", f"{base}/summary"):
        assert client.get(path).status_code == 401, path
    assert client.get("/documents").status_code == 401
    # And it is not advertised on the public listing.
    assert document_id not in [d["id"] for d in client.get("/demo").json()["documents"]]


def test_a_broken_token_is_not_treated_as_an_anonymous_visitor(
    client: TestClient, demo_document_id: str, firebase_mode: None
) -> None:
    """Sending a bad token must fail loudly rather than silently falling back to demo access."""
    response = client.get(f"/documents/{demo_document_id}", headers=bearer("forged"))
    assert response.status_code == 401
    assert response.json()["error"] == "session_expired"


def test_demo_can_be_turned_off(
    client: TestClient,
    demo_document_id: str,
    firebase_mode: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = get_settings().model_copy(
        update={
            "auth_mode": "firebase",
            "firebase_project_id": "clauselens-test",
            "demo_mode_enabled": False,
        }
    )
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    monkeypatch.setattr("app.api.routes.demo.get_settings", lambda: settings)

    assert client.get(f"/documents/{demo_document_id}").status_code == 401
    body = client.get("/demo").json()
    assert body == {"enabled": False, "documents": []}


def test_demo_user_cannot_be_signed_in_as(database: None) -> None:
    """The demo user owns shared documents, so it must have no sign-in identity at all."""
    with SessionLocal() as db:
        user = auth.get_demo_user(db)
        assert user.firebase_uid is None
        same = db.scalar(select(Document).where(Document.is_demo.is_(True)))
        assert same is None or same.user_id == user.id
