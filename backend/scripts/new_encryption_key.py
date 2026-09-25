"""Print a new FILE_ENCRYPTION_KEY (32 random bytes, base64) for backend/.env.

    uv run python -m scripts.new_encryption_key

Keep the key safe and backed up: files encrypted with it cannot be read without it.
"""

from app.services.storage import new_encryption_key

if __name__ == "__main__":
    print(f"FILE_ENCRYPTION_KEY={new_encryption_key()}")
