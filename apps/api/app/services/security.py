from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from app.core.config import settings


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 390_000)
    return "pbkdf2_sha256$390000$" + base64.urlsafe_b64encode(salt).decode() + "$" + base64.urlsafe_b64encode(derived).decode()


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, rounds, salt_text, hash_text = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode())
        expected = base64.urlsafe_b64decode(hash_text.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(rounds))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def new_token() -> tuple[str, str, datetime]:
    token = secrets.token_urlsafe(48)
    return token, hash_token(token), datetime.now(timezone.utc) + timedelta(hours=12)


def hash_token(token: str) -> str:
    return hmac.new(settings.jwt_secret.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()

