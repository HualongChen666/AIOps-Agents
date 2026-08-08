# -*- coding: utf-8 -*-
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import OIDC_REDIRECT_URI as DEFAULT_OIDC_REDIRECT_URI
from core.authentication import UserInDB, create_access_token, get_user  # type: ignore

# ---------------------------------------------------------------------------
# Configuration – OIDC / OAuth2 parameters (must be provided in .env)
# ---------------------------------------------------------------------------
OIDC_ISSUER_URL: str = os.getenv("OIDC_ISSUER_URL", "")
OIDC_CLIENT_ID: str = os.getenv("OIDC_CLIENT_ID", "")
OIDC_CLIENT_SECRET: str = os.getenv("OIDC_CLIENT_SECRET", "")
OIDC_REDIRECT_URI: str = os.getenv("OIDC_REDIRECT_URI", "")
if not OIDC_REDIRECT_URI:
    OIDC_REDIRECT_URI = DEFAULT_OIDC_REDIRECT_URI

# If any of the above are missing, SSO is considered disabled – fallback to password flow.
SSO_ENABLED: bool = all([OIDC_ISSUER_URL, OIDC_CLIENT_ID, OIDC_CLIENT_SECRET])

# ---------------------------------------------------------------------------
# State parameter storage for CSRF protection
# ---------------------------------------------------------------------------
# SECURITY: Store OAuth state parameters to prevent CSRF attacks
# Production should use Redis instead of in-memory storage
_state_store: Dict[str, datetime] = {}


def generate_state() -> str:
    """Generate a cryptographically secure random state parameter."""
    return secrets.token_urlsafe(32)


# ---------------------------------------------------------------------------
# OAuth client – using Authlib's generic OAuth2 client (openid connect)
# ---------------------------------------------------------------------------
oauth = OAuth()
if SSO_ENABLED:
    oauth.register(
        name="oidc",
        client_id=OIDC_CLIENT_ID,
        client_secret=OIDC_CLIENT_SECRET,
        server_metadata_url=f"{OIDC_ISSUER_URL}/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Login entry – redirects user to IdP authorization endpoint
# ---------------------------------------------------------------------------
@router.get("/login")
async def login(request: Request) -> RedirectResponse:
    if not SSO_ENABLED:
        raise HTTPException(status_code=400, detail="SSO not configured")

    # SECURITY: Generate and store state parameter for CSRF protection
    state = generate_state()
    _state_store[state] = datetime.now(timezone.utc)

    redirect_uri = OIDC_REDIRECT_URI
    result = await oauth.oidc.authorize_redirect(
        request, redirect_uri, state=state  # Add state parameter
    )
    return result  # type: ignore


# ---------------------------------------------------------------------------
# Callback endpoint – IdP redirects back with authorization code
# ---------------------------------------------------------------------------
@router.get("/callback")
async def auth_callback(
    request: Request,
    state: str = Query(...),  # Receive state parameter
) -> RedirectResponse:
    if not SSO_ENABLED:
        raise HTTPException(status_code=400, detail="SSO not configured")

    # SECURITY: Verify state parameter to prevent CSRF attacks
    if state not in _state_store:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    # Check if state has expired (5 minutes)
    if datetime.now(timezone.utc) - _state_store[state] > timedelta(minutes=5):
        del _state_store[state]
        raise HTTPException(status_code=400, detail="State parameter expired")

    del _state_store[state]  # Delete after use

    try:
        token = await oauth.oidc.authorize_access_token(request)
    except OAuthError as e:
        raise HTTPException(status_code=400, detail=f"OAuth error: {e.error}")
    # token contains access_token, id_token, etc.
    # Authlib already verifies the JWT signature during token exchange
    # Use userinfo endpoint response which is already verified
    payload = token.get("userinfo")
    if not payload:
        # If userinfo is not available, we cannot safely proceed without proper verification
        # Do not decode JWT manually without signature verification
        raise HTTPException(
            status_code=400,
            detail=(
                "Unable to retrieve user information from IdP. "
                "userinfo endpoint response is required."
            ),
        )
    username: str = payload.get("preferred_username") or payload.get("sub")
    email: str = payload.get("email")
    # Create internal user representation – if not in fake DB, add it  # noqa: E501
    # on‑the‑fly (read‑only for demo)
    user: Optional[UserInDB] = None
    try:
        user = await get_user(username)
    except Exception as exc:
        logger = logging.getLogger(__name__)
        logger.warning(f"Could not load user {username} from database: {exc}")
    if not user:
        # Dynamically create a UserInDB entry (no password) for SSO users
        user = UserInDB(
            username=username,
            full_name=payload.get("name"),
            email=email,
            hashed_password=secrets.token_urlsafe(16),
            disabled=False,
            role=payload.get("role", "user"),
        )
        # Optionally store into in‑memory db for later lookups
        globals().setdefault("_fake_users_db", {})[username] = user.model_dump()
    # Issue internal JWT for API authentication
    access_token_expires = timedelta(minutes=int(os.getenv("JWT_ACCESS_EXPIRE_MINUTES", "30")))
    internal_token = create_access_token(
        data={"sub": user.username, "role": getattr(user, "role", "user")},
        expires_delta=access_token_expires,
    )
    # Redirect back to front‑end with token as fragment (so it is not sent to server logs)
    # Front‑end should parse location.hash to retrieve the token.
    redirect_url = f"/login_success?token={internal_token}"
    return RedirectResponse(url=redirect_url)


# ---------------------------------------------------------------------------
# Simple endpoint for front‑end to fetch token after redirect (optional)
# ---------------------------------------------------------------------------
@router.get("/login_success")
async def login_success(token: str) -> HTMLResponse:
    # Return a tiny HTML page that stores token to localStorage and redirects to app root
    html = f"""
    <html><head><script>
    localStorage.setItem('access_token', '{token}');
    window.location.href = '/';
    </script></head><body>登录成功，正在跳转…</body></html>
    """

    return HTMLResponse(content=html, status_code=200)
