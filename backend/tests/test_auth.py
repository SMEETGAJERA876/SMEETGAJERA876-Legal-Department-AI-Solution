"""Google sign-in (Firebase) and per-user document privacy.

The fake token verifier, the sample claims and the `firebase_mode` fixture live in conftest.py
so the public demo tests (test_demo.py) can sign people in the same way.
"""

import pytest
from fastapi.testclient import TestClient

from app.core import auth
from app.core.config import get_settings
from tests.conftest import PROJECT, TOKENS, bearer, google_claims


def test_check_claims_rejects_other_projects_and_providers() -> None:
    identity = auth.check_claims(google_claims("u1", "u1@example.com"), PROJECT)
    assert identity == auth.Identity("u1", "u1@example.com", "U1")

    email = "u1@example.com"
    other_project = "https://securetoken.google.com/other"
    cases = [
        (google_claims("u1", email, iss=other_project), "invalid_token"),
        (google_claims("u1", email, firebase={"sign_in_provider": "password"}), "google_required"),
        (google_claims("u1", email, firebase={"sign_in_provider": "anonymous"}), "google_required"),
        (google_claims("u1", ""), "email_required"),
        (google_claims("u1", email, email_verified=False), "email_required"),
        (google_claims("", email), "invalid_token"),
    ]
    for claims, code in cases:
        with pytest.raises(auth.AppError) as error:
            auth.check_claims(claims, PROJECT)
        assert error.value.status_code == 401
        assert error.value.code == code


def test_sign_in_required(database: None, client: TestClient, firebase_mode: None) -> None:
    response = client.get("/documents")
    assert response.status_code == 401
    assert response.json()["error"] == "not_signed_in"
    assert client.get("/documents", headers={"Authorization": "Basic abc"}).status_code == 401
    assert client.get("/health").status_code == 200
    # Taxonomy reference data has nothing personal in it and the public demo renders with it.
    for path in ("/documents/types", "/documents/concepts", "/demo"):
        assert client.get(path).status_code == 200, path


def test_invalid_and_non_google_tokens_rejected(
    database: None, client: TestClient, firebase_mode: None
) -> None:
    response = client.get("/documents", headers=bearer("forged"))
    assert response.status_code == 401
    assert response.json()["error"] == "session_expired"

    response = client.get("/documents", headers=bearer("token-password"))
    assert response.status_code == 401
    assert response.json()["error"] == "google_required"


def test_server_without_project_id_says_so(
    database: None, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings().model_copy(
        update={"auth_mode": "firebase", "firebase_project_id": ""}
    )
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    response = client.get("/documents", headers=bearer("token-alice"))
    assert response.status_code == 503
    assert response.json()["error"] == "auth_not_configured"


def test_documents_are_private_to_their_owner(
    database: None, client: TestClient, firebase_mode: None, sample_pdf: bytes
) -> None:
    alice, bob = bearer("token-alice"), bearer("token-bob")
    response = client.post(
        "/documents",
        headers=alice,
        files={"file": ("alice_agreement.pdf", sample_pdf, "application/pdf")},
    )
    assert response.status_code == 201, response.text
    document_id = response.json()["id"]
    base = f"/documents/{document_id}"

    # The owner can use it.
    assert client.get(base, headers=alice).json()["status"] == "ready"
    assert document_id in [d["id"] for d in client.get("/documents", headers=alice).json()]
    assert client.get(f"{base}/file", headers=alice).status_code == 200

    # Anyone else gets "not found" everywhere — not even a hint that it exists.
    assert document_id not in [d["id"] for d in client.get("/documents", headers=bob).json()]
    requests = [
        ("GET", base, None),
        ("GET", f"{base}/file", None),
        ("GET", f"{base}/file?download=true", None),
        ("GET", f"{base}/overview", None),
        ("GET", f"{base}/normalized", None),
        ("GET", f"{base}/search?q=notice", None),
        ("POST", f"{base}/ask", {"question": "What is the notice period?"}),
        ("GET", f"{base}/questions", None),
        ("GET", f"{base}/issues", None),
        ("POST", f"{base}/repair", {"issue_ids": []}),
        ("GET", f"{base}/summary", None),
        ("PUT", f"{base}/classification", {"document_type_id": "employment_agreement"}),
        ("DELETE", base, None),
    ]
    for method, path, body in requests:
        response = client.request(method, path, headers=bob, json=body)
        assert response.status_code == 404, (method, path, response.status_code)
        assert response.json()["error"] == "not_found", (method, path)

    # Bob's failed delete left it alone; Alice can delete her own document.
    assert client.get(base, headers=alice).status_code == 200
    assert client.delete(base, headers=alice).status_code == 204
    assert client.get(base, headers=alice).status_code == 404


def test_same_google_account_is_the_same_user(
    database: None, client: TestClient, firebase_mode: None, sample_pdf: bytes
) -> None:
    response = client.post(
        "/documents",
        headers=bearer("token-bob"),
        files={"file": ("bob.pdf", sample_pdf, "application/pdf")},
    )
    document_id = response.json()["id"]
    # A later session (new token, same Google account) still sees the document.
    TOKENS["token-bob-later"] = google_claims("bob", "bob@example.com", name="Bob B.")
    try:
        listed = client.get("/documents", headers=bearer("token-bob-later")).json()
        assert document_id in [d["id"] for d in listed]
    finally:
        del TOKENS["token-bob-later"]
        client.delete(f"/documents/{document_id}", headers=bearer("token-bob"))
