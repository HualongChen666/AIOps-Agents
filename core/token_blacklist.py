# -*- coding: utf-8 -*-
"""Token blacklist management for JWT revocation."""

from datetime import datetime, timedelta
from typing import Optional

from core.auth_db import SessionLocal, TokenBlacklist


def is_blacklisted(jti: str) -> bool:
    """Return True if the given jti has been revoked."""
    if not jti:
        return False
    db = SessionLocal()
    try:
        return (
            db.query(TokenBlacklist)
            .filter(TokenBlacklist.jti == jti)
            .first()
            is not None
        )
    finally:
        db.close()


def blacklist_jti(jti: str, expires_at: Optional[datetime] = None) -> None:
    """Add a jti to the blacklist. Optionally record when it naturally expires."""
    if not jti:
        return
    db = SessionLocal()
    try:
        if not db.query(TokenBlacklist).filter(TokenBlacklist.jti == jti).first():
            db.add(TokenBlacklist(jti=jti, expires_at=expires_at))
            db.commit()
    finally:
        db.close()


def cleanup_expired() -> int:
    """Remove blacklist entries whose expires_at is in the past."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        rows = (
            db.query(TokenBlacklist)
            .filter(TokenBlacklist.expires_at < now)
            .delete(synchronize_session=False)
        )
        db.commit()
        return rows
    finally:
        db.close()


def blacklist_token(token: str, secret: str, algorithm: str) -> None:
    """Decode a JWT and blacklist its jti (without full validation of exp/iat)."""
    import jwt

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[algorithm],
            options={"verify_exp": False, "verify_iat": False, "verify_aud": False},
        )
    except Exception:
        return
    jti = payload.get("jti")
    exp = payload.get("exp")
    exp_dt = datetime.utcfromtimestamp(exp) if exp else None
    if jti:
        blacklist_jti(jti, exp_dt)
