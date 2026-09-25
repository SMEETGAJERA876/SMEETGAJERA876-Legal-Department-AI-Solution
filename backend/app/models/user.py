from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base_columns import CreatedAtMixin, IdMixin


class User(IdMixin, CreatedAtMixin, Base):
    """A person signed in with Google (Firebase Authentication). Documents belong to one user."""

    __tablename__ = "users"

    firebase_uid: Mapped[str | None] = mapped_column(String(128), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    display_name: Mapped[str | None] = mapped_column(String(200))
