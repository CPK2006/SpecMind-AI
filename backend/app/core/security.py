import bcrypt
import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import settings


# Used only to verify passwords created by the old implementation.
# Never use this legacy key to sign new JWTs.
_LEGACY_SECRET = "specmind-ai-secret-key-for-jwt-token-auth"


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")

    if len(password_bytes) > 72:
        raise ValueError("Password must not exceed 72 UTF-8 bytes.")

    return bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt(),
    ).decode("utf-8")


def is_legacy_password_hash(hashed_password: str) -> bool:
    return (
        len(hashed_password) == 64
        and all(c in "0123456789abcdefABCDEF" for c in hashed_password)
    )


def verify_password(password: str, hashed_password: str) -> bool:
    if is_legacy_password_hash(hashed_password):
        legacy_value = hashlib.sha256(
            f"specmind_salt_{password}_{_LEGACY_SECRET}".encode("utf-8")
        ).hexdigest()

        return hmac.compare_digest(legacy_value, hashed_password)

    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    payload = {
        "sub": subject,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.algorithm],
    )
