"""JWT issuance/verification and password hashing for Vestra.

Password hashing uses the standard library's PBKDF2-HMAC-SHA256 (no extra
dependency) with a per-password random salt. JWTs are signed with the configured
``JWT_SECRET`` using PyJWT (already a project dependency).
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt

from app.config import get_settings

_PBKDF2_ROUNDS = 200_000
_SALT_BYTES = 16


# --- Password hashing ----------------------------------------------------

def hash_password(password: str) -> str:
    """Return a ``pbkdf2_sha256$rounds$salt$hash`` encoded string."""
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${_PBKDF2_ROUNDS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    """Constant-time verify a password against an encoded hash."""
    try:
        algo, rounds_s, salt_hex, hash_hex = encoded.split("$")
        if algo != "pbkdf2_sha256":
            return False
        rounds = int(rounds_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds)
        return hmac.compare_digest(digest, expected)
    except (ValueError, AttributeError):
        return False


# --- JWT -----------------------------------------------------------------

def create_access_token(user_id: str, extra: Optional[Dict[str, Any]] = None) -> str:
    """Mint a signed JWT whose subject is ``user_id``."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and verify a JWT. Raises ``jwt.PyJWTError`` on any problem."""
    settings = get_settings()
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
]
