"""Audit log: every access to or change of a document is recorded (models/audit.py).

Users can read their own log (GET /account/activity); it is deleted with their account.
"""

import uuid
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditEvent

UPLOAD = "upload"
VIEW_FILE = "view_file"
DOWNLOAD_FILE = "download_file"
DOWNLOAD_SUMMARY = "download_summary"
REPAIR = "repair"
DELETE = "delete"
CHANGE_TYPE = "change_type"
ACCOUNT_CREATED = "account_created"
DELETE_ALL_DATA = "delete_all_data"
RETENTION_DELETE = "retention_delete"

LABELS = {
    UPLOAD: "Uploaded a document",
    VIEW_FILE: "Opened a document",
    DOWNLOAD_FILE: "Downloaded a PDF",
    DOWNLOAD_SUMMARY: "Downloaded a summary PDF",
    REPAIR: "Created a corrected copy",
    DELETE: "Deleted a document",
    CHANGE_TYPE: "Changed the document type",
    ACCOUNT_CREATED: "Signed in for the first time",
    DELETE_ALL_DATA: "Deleted all documents",
    RETENTION_DELETE: "Deleted automatically after the retention period",
}


def client_ip(request: Request | None) -> str | None:
    if request is None or request.client is None:
        return None
    return request.client.host


def record(
    db: Session,
    action: str,
    *,
    user_id: uuid.UUID | None,
    document_id: uuid.UUID | None = None,
    request: Request | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    """Add an event to the session; it is saved with the caller's commit."""
    db.add(
        AuditEvent(
            user_id=user_id,
            document_id=document_id,
            action=action,
            ip_address=client_ip(request),
            detail=detail,
        )
    )
