"""Stores uploaded files on disk under random names. Uploaded files are never executed.

The file format is decided from the file's content, never from its name or declared type.

Encryption at rest: with FILE_ENCRYPTION_KEY set, every stored file is encrypted with
AES-256-GCM (authenticated, so tampering is detected). The key lives outside the database, so a
copy of the uploads folder or of the database alone reveals nothing. This module is the only
code that touches stored files; everything else reads and writes bytes through it. Files stored
before encryption was switched on stay readable.
"""

import base64
import logging
import os
import uuid
from functools import lru_cache
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import UploadFile

from app.core.config import get_settings
from app.core.errors import AppError, ValidationError
from app.services.parsing import FORMAT_LABELS, HEADER_BYTES, SUPPORTED_FORMATS, detect_format

READ_BLOCK_BYTES = 1024 * 1024
MAX_FILENAME_CHARS = 200
ENCRYPTED_MAGIC = b"CLENC1"
NONCE_BYTES = 12
KEY_BYTES = 32

logger = logging.getLogger("clauselens.storage")


@lru_cache
def _cipher() -> AESGCM | None:
    key = get_settings().file_encryption_key.strip()
    if not key:
        logger.warning("FILE_ENCRYPTION_KEY is not set: uploaded files are stored unencrypted.")
        return None
    raw = base64.urlsafe_b64decode(key + "=" * (-len(key) % 4))
    if len(raw) != KEY_BYTES:
        raise ValueError("FILE_ENCRYPTION_KEY must be 32 bytes, base64-encoded.")
    return AESGCM(raw)


def encryption_enabled() -> bool:
    return _cipher() is not None


def new_encryption_key() -> str:
    return base64.urlsafe_b64encode(os.urandom(KEY_BYTES)).decode().rstrip("=")


def _encrypt(data: bytes) -> bytes:
    cipher = _cipher()
    if cipher is None:
        return data
    nonce = os.urandom(NONCE_BYTES)
    return ENCRYPTED_MAGIC + nonce + cipher.encrypt(nonce, data, ENCRYPTED_MAGIC)


def _decrypt(blob: bytes) -> bytes:
    if not blob.startswith(ENCRYPTED_MAGIC):
        return blob  # stored before encryption was switched on
    cipher = _cipher()
    if cipher is None:
        raise AppError(
            500, "file_encrypted", "This file is encrypted and the server has no key to open it."
        )
    nonce = blob[len(ENCRYPTED_MAGIC) : len(ENCRYPTED_MAGIC) + NONCE_BYTES]
    return cipher.decrypt(nonce, blob[len(ENCRYPTED_MAGIC) + NONCE_BYTES :], ENCRYPTED_MAGIC)


def read_file(stored_filename: str) -> bytes:
    path = stored_path(stored_filename)
    if not path.exists():
        raise FileNotFoundError(stored_filename)
    return _decrypt(path.read_bytes())


def write_file(stored_filename: str, data: bytes) -> None:
    path = stored_path(stored_filename)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(_encrypt(data))
    temporary.replace(path)


def delete_file(stored_filename: str) -> None:
    stored_path(stored_filename).unlink(missing_ok=True)


def file_exists(stored_filename: str) -> bool:
    return stored_path(stored_filename).exists()


def upload_dir() -> Path:
    path = Path(get_settings().upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def stored_path(stored_filename: str) -> Path:
    return upload_dir() / stored_filename


def new_stored_filename(fmt: str = "pdf") -> str:
    return f"{uuid.uuid4().hex}.{fmt}"


def safe_display_name(filename: str | None) -> str:
    name = Path(filename or "document.pdf").name.strip() or "document.pdf"
    cleaned = "".join(ch for ch in name if ch.isprintable() and ch not in '<>:"/\\|?*')
    return cleaned[:MAX_FILENAME_CHARS] or "document.pdf"


def _check_format(path: Path) -> str:
    with path.open("rb") as file:
        header = file.read(HEADER_BYTES)
    full = path.read_bytes() if header.startswith(b"PK\x03\x04") else None
    fmt = detect_format(header, full)
    if fmt is None:
        raise ValidationError(
            "unsupported_file_type",
            "This file type isn't recognised. Please upload the document as a PDF.",
            status_code=415,
        )
    if fmt not in SUPPORTED_FORMATS:
        raise ValidationError(
            "unsupported_file_type",
            f"{FORMAT_LABELS.get(fmt, fmt.upper())} files are not supported yet. Please upload "
            "the document as a PDF (for example: File → Save as PDF).",
            status_code=415,
        )
    return fmt


async def save_upload(file: UploadFile) -> tuple[str, int, str]:
    """Validate and save an upload. Returns (stored_filename, size_in_bytes, format)."""
    max_bytes = get_settings().max_upload_size_mb * 1024 * 1024
    temporary = stored_path(f"{uuid.uuid4().hex}.upload")
    size = 0
    try:
        with temporary.open("wb") as out:
            while block := await file.read(READ_BLOCK_BYTES):
                size += len(block)
                if size > max_bytes:
                    raise ValidationError(
                        "file_too_large",
                        f"This file is larger than {get_settings().max_upload_size_mb} MB. "
                        "Try compressing it or splitting it into smaller parts.",
                        status_code=413,
                    )
                out.write(block)
        if size == 0:
            raise ValidationError("empty_file", "The uploaded file is empty.")
        fmt = _check_format(temporary)
        stored_filename = new_stored_filename(fmt)
        write_file(stored_filename, temporary.read_bytes())
    finally:
        temporary.unlink(missing_ok=True)
    return stored_filename, size, fmt
