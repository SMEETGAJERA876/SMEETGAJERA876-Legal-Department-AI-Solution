"""Test configuration.

Integration tests use a separate database (TEST_DATABASE_URL, default: clauselens_test on the
dev server from scripts/dev_db.py) and are skipped when it is not reachable.
"""

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://clauselens:clauselens@localhost:5433/clauselens_test",
)
# Must be set before the app (and its cached settings) is imported.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="clauselens-uploads-")
os.environ["AI_PROVIDER"] = "none"
os.environ["AUTH_MODE"] = "disabled"
# Every test runs with encryption at rest on; rate limits are tested separately.
os.environ["FILE_ENCRYPTION_KEY"] = "zGH0yQ7l3nq7qYfJ0mO9b4bWm7mK1g6yH2u0cQy9V4E"
os.environ["RATE_LIMIT_ENABLED"] = "false"
# Uploads are processed right after the request; the queue has its own tests.
os.environ["PROCESSING_MODE"] = "inline"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402, F401
from app.db.base import Base  # noqa: E402
from app.db.session import check_database_connection, engine  # noqa: E402
from app.main import app  # noqa: E402

SAMPLE_PDF = Path(__file__).resolve().parents[2] / "samples" / "employment_agreement.pdf"


@pytest.fixture(scope="session")
def database() -> Iterator[None]:
    if not check_database_connection():
        pytest.skip("Test database not reachable. Run: uv run scripts/dev_db.py start")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="session")
def sample_pdf() -> bytes:
    if not SAMPLE_PDF.exists():
        from scripts.make_sample_pdf import build_employment_agreement

        build_employment_agreement(SAMPLE_PDF)
    return SAMPLE_PDF.read_bytes()


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session")
def processed_document_id(database: None, client: TestClient, sample_pdf: bytes) -> str:
    """Upload the sample agreement once; background processing runs inside the request."""
    response = client.post(
        "/documents",
        files={"file": ("employment_agreement.pdf", sample_pdf, "application/pdf")},
    )
    assert response.status_code == 201, response.text
    document_id: str = response.json()["id"]
    status = client.get(f"/documents/{document_id}").json()
    assert status["status"] == "ready", status
    return document_id


# ---------------------------------------------------------------------------
# Google sign-in. Real Firebase tokens can't be minted in tests, so the signature check is
# replaced by a fake that maps a token string to claims; everything after it (claim checks,
# users, ownership, the public demo) is real. Used by test_auth.py and test_demo.py.
# ---------------------------------------------------------------------------

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
    from app.core import auth
    from app.core.config import get_settings

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
