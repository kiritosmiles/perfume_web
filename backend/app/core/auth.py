import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt as _bcrypt
from jose import JWTError, jwt

from app.core.config import settings

ACCESS_TTL = timedelta(hours=1)
REFRESH_TTL = timedelta(days=7)
ALGORITHM = "HS256"
_BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    """Hash password with bcrypt (rounds=12). Returns hash string."""
    salt = _bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    return _bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against bcrypt hash."""
    return _bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user_id: str, feature_tier: str = "free") -> str:
    """Create HS256 JWT access token. exp=1h.

    Payload: {sub, type:'access', iat, exp, tier}
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + ACCESS_TTL,
        "tier": feature_tier,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> tuple[str, str]:
    """Create refresh token. Returns (raw_token, token_hash).
    raw_token: JWT with exp=7d, payload includes jti (unique id).
    token_hash: SHA-256 hex digest of raw_token (for PG storage).
    """
    jti = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": jti,
        "iat": now,
        "exp": now + REFRESH_TTL,
    }
    raw = jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, token_hash


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Returns payload dict. Raises ValueError on any failure."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")
