"""Google sign-in (Firebase) and per-user document privacy.

Real Firebase tokens can't be minted in tests, so the signature check is replaced by a fake that
maps a token string to claims; everything after it (claim checks, users, ownership) is real.
"""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core import auth
from app.core.config import get_settings

PROJECT = "clauselens-test"


def google_claims(uid: str, email: str, **overrides: Any) -> dict[str, Any]:
    claims: dict[str, Any] = {
        "iss": f"https://securetoken.google.com/{PROJECT}",
        "aud": PROJECT,
        "sub": uid,
        "email": email,
        "email_verified": True,
        "name": uid.title(),
        "firebase": {"sign_in_provider": "google.com"},
    }
    claims.update(overrides)
    return claims


TOKENS = {
    "token-alice": google_claims("alice", "alice@example.com"),
    "token-bob": google_claims("bob", "bob@example.com"),
    "token-password": google_claims(
        "carol", "carol@example.com", firebase={"sign_in_provider": "password"}
    ),
}


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def firebase_mode(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    settings = get_settings().model_copy(
        update={"auth_mode": "firebase", "firebase_project_id": PROJECT}
    )
    monkeypatch.setattr(auth, "get_settings", lambda: settings)

    def fake_verify(token: str, request: Any, audience: str, **_: Any) -> dict[str, Any]:
        assert audience == PROJECT
        if token not in TOKENS:
            raise ValueError("Could not verify token signature.")
        return TOKENS[token]

    monkeypatch.setattr(auth.id_token, "verify_firebase_token", fake_verify)
    yield


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
    for path in ("/documents", "/documents/types", "/documents/concepts"):
        response = client.get(path)
        assert response.status_code == 401, path
        assert response.json()["error"] == "not_signed_in"
    assert client.get("/documents", headers={"Authorization": "Basic abc"}).status_code == 401
    assert client.get("/health").status_code == 200


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
