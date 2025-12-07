from datetime import datetime, timedelta, timezone
from typing import Any
from jose import jwt
import bcrypt
import uuid
from ..core.config import settings
from ..db.database import get_db


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a bcrypt hash."""
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_token(subject: str, email: str, role: str, expires_delta: timedelta, token_type: str) -> dict:
    now = _utcnow()
    expire = now + expires_delta
    jti = str(uuid.uuid4())
    payload = {
        "sub": subject,
        "email": email,
        "role": role,
        "type": token_type,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return {"token": token, "jti": jti, "exp": expire}


def create_access_token(subject: str, email: str, role: str) -> dict:
    return create_token(subject, email, role, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), "access")


def create_refresh_token(subject: str, email: str, role: str) -> dict:
    return create_token(subject, email, role, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS), "refresh")

async def is_token_blacklisted(jti: str) -> bool:
    db = await get_db()
    doc = await db.tokens_blacklist.find_one({"jti": jti})
    return doc is not None

async def blacklist_token(jti: str, exp: datetime):
    db = await get_db()
    await db.tokens_blacklist.update_one({"jti": jti}, {"$set": {"jti": jti, "exp": exp}}, upsert=True)
