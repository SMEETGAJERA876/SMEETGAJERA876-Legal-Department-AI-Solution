"""Give documents uploaded without sign-in (AUTH_MODE=disabled) to a Google account.

The account must have signed in once so its user row exists:

    uv run python -m scripts.assign_documents you@gmail.com
"""

import argparse

from sqlalchemy import select, update

from app.core.auth import LOCAL_USER_UID
from app.db.session import SessionLocal
from app.models import Document, User


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("email", help="email of the Google account that should own the documents")
    args = parser.parse_args()

    with SessionLocal() as db:
        local = db.scalar(select(User).where(User.firebase_uid == LOCAL_USER_UID))
        owner = db.scalar(select(User).where(User.email == args.email))
        if owner is None or owner.firebase_uid == LOCAL_USER_UID:
            raise SystemExit(f"No Google account {args.email!r} yet. Sign in once, then retry.")
        if local is None:
            raise SystemExit("There are no local (signed-out) documents to move.")
        result = db.execute(
            update(Document).where(Document.user_id == local.id).values(user_id=owner.id)
        )
        db.commit()
        print(f"Moved {result.rowcount} document(s) to {args.email}.")  # type: ignore[attr-defined]


if __name__ == "__main__":
    main()
