"""Encryption at rest, security headers, rate limits, production safety checks, the audit log,
the user's own activity and "delete all my data", retention and crash recovery."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.core import security
from app.core.config import Settings, get_settings
from app.core.security import (
    InsecureConfigurationError,
    Limit,
    RateLimiter,
    check_production_settings,
)
from app.db.session import SessionLocal
from app.models import AuditEvent, Document, DocumentStatus
from app.services import lifecycle, storage


def upload(client: TestClient, pdf: bytes, name: str = "private.pdf") -> str:
    response = client.post("/documents", files={"file": (name, pdf, "application/pdf")})
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def stored_filename(document_id: str) -> str:
    with SessionLocal() as db:
        document = db.get(Document, __import__("uuid").UUID(document_id))
        assert document is not None
        return document.stored_filename


def test_files_are_encrypted_at_rest(database: None, client: TestClient, sample_pdf: bytes) -> None:
    assert storage.encryption_enabled()
    document_id = upload(client, sample_pdf)
    on_disk = storage.stored_path(stored_filename(document_id)).read_bytes()
    assert on_disk.startswith(storage.ENCRYPTED_MAGIC)
    assert b"%PDF" not in on_disk[:64]
    assert b"Employment" not in on_disk  # no plaintext leaks
    # ...but the owner gets the original back, byte for byte.
    assert client.get(f"/documents/{document_id}/file").content == sample_pdf
    client.delete(f"/documents/{document_id}")


def test_tampered_file_is_rejected() -> None:
    storage.write_file("tamper-test.pdf", b"%PDF-1.4 secret")
    path = storage.stored_path("tamper-test.pdf")
    blob = bytearray(path.read_bytes())
    blob[-1] ^= 0x01
    path.write_bytes(bytes(blob))
    with pytest.raises(Exception):  # noqa: B017 - InvalidTag from the AES-GCM layer
        storage.read_file("tamper-test.pdf")
    storage.delete_file("tamper-test.pdf")


def test_files_stored_before_encryption_stay_readable() -> None:
    storage.stored_path("legacy.pdf").write_bytes(b"%PDF-1.4 legacy")
    assert storage.read_file("legacy.pdf") == b"%PDF-1.4 legacy"
    storage.delete_file("legacy.pdf")


def test_security_headers(client: TestClient) -> None:
    response = client.get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["Cache-Control"] == "no-store"


def test_rate_limiter_window() -> None:
    limiter = RateLimiter()
    limit = Limit("test", 3, 60)
    assert all(limiter.check("1.2.3.4", limit, now=t) is None for t in (0, 1, 2))
    wait = limiter.check("1.2.3.4", limit, now=3)
    assert wait is not None and 56 < wait <= 60
    assert limiter.check("5.6.7.8", limit, now=3) is None  # other clients are unaffected
    assert limiter.check("1.2.3.4", limit, now=61) is None  # the window slides


def test_rate_limit_returns_friendly_429(
    database: None, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings().model_copy(update={"rate_limit_enabled": True})
    monkeypatch.setattr(security, "get_settings", lambda: settings)
    monkeypatch.setattr(security, "DEFAULT_LIMIT", Limit("default", 2, 60))
    security.rate_limiter.reset()
    try:
        assert client.get("/documents").status_code == 200
        assert client.get("/documents").status_code == 200
        response = client.get("/documents")
        assert response.status_code == 429
        assert response.json()["error"] == "too_many_requests"
        assert int(response.headers["Retry-After"]) >= 1
        assert client.get("/health").status_code == 200  # health checks are never limited
    finally:
        security.rate_limiter.reset()


def test_production_refuses_insecure_settings() -> None:
    insecure = Settings(environment="production", auth_mode="disabled", file_encryption_key="")
    with pytest.raises(InsecureConfigurationError) as error:
        check_production_settings(insecure)
    assert "AUTH_MODE" in str(error.value) and "FILE_ENCRYPTION_KEY" in str(error.value)
    secure = Settings(
        environment="production",
        auth_mode="firebase",
        firebase_project_id="demo",
        file_encryption_key=storage.new_encryption_key(),
        cors_origins=["https://clauselens.example"],
        rate_limit_enabled=True,
    )
    check_production_settings(secure)  # does not raise


def test_audit_log_and_my_activity(database: None, client: TestClient, sample_pdf: bytes) -> None:
    document_id = upload(client, sample_pdf, "audited.pdf")
    client.get(f"/documents/{document_id}/file")
    client.get(f"/documents/{document_id}/file", params={"download": "true"})
    client.get(f"/documents/{document_id}/summary")
    client.delete(f"/documents/{document_id}")

    activity = client.get("/account/activity").json()
    mine = [a for a in activity if a["document_id"] == document_id]
    actions = [a["action"] for a in mine]
    for action in ("upload", "view_file", "download_file", "download_summary", "delete"):
        assert action in actions, actions
    assert all(a["label"] for a in mine)


def test_delete_all_my_data(database: None, client: TestClient, sample_pdf: bytes) -> None:
    ids = [upload(client, sample_pdf, f"erase-{i}.pdf") for i in range(2)]
    files = [stored_filename(i) for i in ids]
    response = client.delete("/account/documents")
    assert response.status_code == 200
    assert response.json()["deleted_documents"] >= 2
    assert client.get("/documents").json() == []
    assert not any(storage.file_exists(f) for f in files)
    assert any(a["action"] == "delete_all_data" for a in client.get("/account/activity").json())


def test_retention_deletes_old_documents(
    database: None, client: TestClient, sample_pdf: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    old, new = upload(client, sample_pdf, "old.pdf"), upload(client, sample_pdf, "new.pdf")
    with SessionLocal() as db:
        db.execute(
            update(Document)
            .where(Document.id == __import__("uuid").UUID(old))
            .values(created_at=datetime.now(UTC) - timedelta(days=40))
        )
        db.commit()
    settings = get_settings().model_copy(update={"retention_days": 30})
    monkeypatch.setattr(lifecycle, "get_settings", lambda: settings)
    assert lifecycle.apply_retention() == 1
    assert client.get(f"/documents/{old}").status_code == 404
    assert client.get(f"/documents/{new}").status_code == 200
    with SessionLocal() as db:
        logged = db.scalars(
            select(AuditEvent.action).where(AuditEvent.document_id == __import__("uuid").UUID(old))
        )
        assert "retention_delete" in list(logged)
    client.delete(f"/documents/{new}")


def test_interrupted_processing_is_resumed(
    database: None, client: TestClient, sample_pdf: bytes
) -> None:
    document_id = upload(client, sample_pdf, "interrupted.pdf")
    with SessionLocal() as db:  # simulate a crash mid-processing
        db.execute(
            update(Document)
            .where(Document.id == __import__("uuid").UUID(document_id))
            .values(status=DocumentStatus.PROCESSING, status_detail="Reading pages")
        )
        db.commit()
    assert lifecycle.resume_unfinished() >= 1
    assert client.get(f"/documents/{document_id}").json()["status"] == "ready"
    client.delete(f"/documents/{document_id}")
