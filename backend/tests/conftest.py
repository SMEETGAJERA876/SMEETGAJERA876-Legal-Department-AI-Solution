"""Test configuration.

Integration tests use a separate database (TEST_DATABASE_URL, default: clauselens_test on the
dev server from scripts/dev_db.py) and are skipped when it is not reachable.
"""

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

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
