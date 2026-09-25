"""Google sign-in through Firebase Authentication.

The browser signs in with Google (Firebase JS SDK) and sends the Firebase ID token as
`Authorization: Bearer <token>`. Every request under /documents is verified here:

- signature against Google's public keys (cached), audience = our Firebase project,
  issuer = https://securetoken.google.com/<project>, not expired;
- the sign-in method must be Google (the only provider this app enables).

Documents are private to their owner: any /documents/{document_id} route for a document the
user doesn't own answers 404, so it doesn't even reveal that the document exists.

AUTH_MODE=disabled runs everything as one local user — for local development only.
"""

import threading
import time
import uuid
from dataclasses import dataclass
from typing import Annotated, Any

import requests
from fastapi import Depends, Header, Request
from google.auth import exceptions as google_exceptions
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError
from app.db.session import get_db
from app.models import Document, User
from app.services import audit

LOCAL_USER_UID = "local-dev"
LOCAL_USER_EMAIL = "local-dev@localhost"
GOOGLE_PROVIDER = "google.com"
CERT_CACHE_SECONDS = 3600
CLOCK_SKEW_SECONDS = 10


@dataclass(frozen=True)
class Identity:
    uid: str
    email: str
    name: str | None


class _CachingRequest(google_requests.Request):
    """google-auth transport that caches Google's public signing keys (they rotate rarely),
    so verifying a token doesn't cost a network round trip on every request."""

    def __init__(self) -> None:
        super().__init__(requests.Session())
        self._cache: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def __call__(self, url: str, method: str = "GET", **kwargs: Any) -> Any:  # type: ignore[override]
        if method != "GET":
            return super().__call__(url, method=method, **kwargs)
        with self._lock:
            cached = self._cache.get(url)
            if cached and time.monotonic() - cached[0] < CERT_CACHE_SECONDS:
                return cached[1]
        response = super().__call__(url, method=method, **kwargs)
        if response.status == 200:
            with self._lock:
                self._cache[url] = (time.monotonic(), response)
        return response


_transport = _CachingRequest()


def _unauthorized(code: str, message: str) -> AppError:
    return AppError(401, code, message)


def check_claims(claims: dict[str, Any], project_id: str) -> Identity:
    """Checks beyond the signature: issuer, subject, Google as the sign-in method, email."""
    if claims.get("iss") != f"https://securetoken.google.com/{project_id}":
        raise _unauthorized(
            "invalid_token", "This sign-in is for a different app. Please sign in again."
        )
    uid = claims.get("sub") or claims.get("user_id")
    if not isinstance(uid, str) or not uid:
        raise _unauthorized(
            "invalid_token", "Your sign-in could not be verified. Please sign in again."
        )
    provider = (claims.get("firebase") or {}).get("sign_in_provider")
    if provider != GOOGLE_PROVIDER:
        raise _unauthorized("google_required", "Please sign in with your Google account.")
    email = claims.get("email")
    if not isinstance(email, str) or not email or claims.get("email_verified") is False:
        raise _unauthorized("email_required", "Your Google account needs a verified email address.")
    name = claims.get("name")
    return Identity(uid, email, name if isinstance(name, str) else None)


def verify_firebase_token(token: str) -> Identity:
    project_id = get_settings().firebase_project_id
    if not project_id:
        raise AppError(
            503,
            "auth_not_configured",
            "Sign-in is not set up on the server yet (FIREBASE_PROJECT_ID is missing).",
        )
    try:
        claims = id_token.verify_firebase_token(
            token, _transport, audience=project_id, clock_skew_in_seconds=CLOCK_SKEW_SECONDS
        )
    except (ValueError, google_exceptions.GoogleAuthError) as error:
        raise _unauthorized(
            "session_expired", "Your sign-in has expired or is not valid. Please sign in again."
        ) from error
    if not claims:
        raise _unauthorized(
            "invalid_token", "Your sign-in could not be verified. Please sign in again."
        )
    return check_claims(dict(claims), project_id)


def _user_for(db: Session, identity: Identity) -> User:
    user = db.scalar(select(User).where(User.firebase_uid == identity.uid))
    if user is None:
        user = User(firebase_uid=identity.uid, email=identity.email, display_name=identity.name)
        db.add(user)
        db.flush()
        audit.record(db, audit.ACCOUNT_CREATED, user_id=user.id)
    else:
        user.email = identity.email
        user.display_name = identity.name
    db.commit()
    return user


def get_current_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if get_settings().auth_mode == "disabled":
        identity = Identity(LOCAL_USER_UID, LOCAL_USER_EMAIL, "Local user")
    else:
        scheme, _, token = (authorization or "").partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise _unauthorized("not_signed_in", "Please sign in with Google to use ClauseLens.")
        identity = verify_firebase_token(token.strip())
    user = _user_for(db, identity)
    request.state.user = user
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_document_access(
    request: Request, db: Annotated[Session, Depends(get_db)], user: CurrentUser
) -> None:
    """Router-level guard: a {document_id} that belongs to someone else is 'not found'."""
    raw = request.path_params.get("document_id")
    if raw is None:
        return
    try:
        document_id = uuid.UUID(str(raw))
    except ValueError:
        return  # the route's own validation answers 422
    row = db.execute(select(Document.user_id).where(Document.id == document_id)).first()
    if row is not None and row[0] != user.id:
        raise NotFoundError("This document doesn't exist or has been deleted.")


def current_user(request: Request) -> User:
    """The user already authenticated by the router guard (for handlers that need it)."""
    user: User = request.state.user
    return user
