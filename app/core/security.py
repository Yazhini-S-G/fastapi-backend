import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from app.constants import UTF_8_ENCODING

PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 15


def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode(UTF_8_ENCODING)).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a SHA-256 hashed password."""
    return hashlib.sha256(plain_password.encode(UTF_8_ENCODING)).hexdigest() == hashed_password


def generate_password_reset_token() -> tuple[str, str, datetime]:
    token = secrets.token_urlsafe(32)
    token_hash = hash_reset_token(token)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    return token, token_hash, expires_at


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode(UTF_8_ENCODING)).hexdigest()


def verify_password_reset_token(token: str, token_hash: str | None, expires_at: datetime | None) -> bool:
    if token_hash is None or expires_at is None:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return False
    return hmac.compare_digest(hash_reset_token(token), token_hash)
