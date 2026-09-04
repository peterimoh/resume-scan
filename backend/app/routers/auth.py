from __future__ import annotations

import base64
import json
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse

from .. import config, db, security
from ..deps import get_current_user
from ..schemas import (
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetResponse,
    UserCreate,
    UserLogin,
    UserOut,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=config.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite="lax",
        max_age=config.SESSION_MAX_AGE_DAYS * 86400,
        path="/",
    )


def _user_out(user: dict) -> UserOut:
    return UserOut(id=user["id"], email=user["email"], created_at=user["created_at"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: UserCreate, response: Response) -> UserOut:
    if config.SIGNUP_CODE and body.signup_code != config.SIGNUP_CODE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or missing invite code")
    if db.get_user_by_email(body.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user_id = db.create_user(body.email, security.hash_password(body.password))
    db.migrate_legacy_resumes_for_user(user_id)
    token = security.new_session_token()
    db.create_session(user_id, token)
    _set_session_cookie(response, token)
    return _user_out(db.get_user_by_id(user_id))


@router.post("/login", response_model=UserOut)
def login(body: UserLogin, response: Response) -> UserOut:
    user = db.get_user_by_email(body.email)
    if not user or not security.verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = security.new_session_token()
    db.create_session(user["id"], token)
    _set_session_cookie(response, token)
    return _user_out(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    session_token: str | None = Cookie(default=None, alias=config.SESSION_COOKIE_NAME),
) -> None:
    if session_token:
        db.delete_session(session_token)
    response.delete_cookie(config.SESSION_COOKIE_NAME, path="/")


@router.get("/me", response_model=UserOut)
def me(user: dict = Depends(get_current_user)) -> UserOut:
    return _user_out(user)


# --- Password reset -------------------------------------------------------


@router.post("/forgot-password", response_model=PasswordResetResponse)
def forgot_password(body: PasswordResetRequest) -> PasswordResetResponse:
    """Always responds ok (no email enumeration). Creates a one-time reset
    token for the account when it exists. Without a mailer configured, the
    token is returned in the response so the flow stays usable in dev."""
    user = db.get_user_by_email(body.email)
    reset_token: str | None = None
    note: str | None = None
    if user:
        token = security.new_token()
        expires = datetime.now(timezone.utc) + timedelta(
            minutes=config.PASSWORD_RESET_TTL_MINUTES
        )
        db.create_password_reset_token(
            user["id"], security.hash_token(token), expires.isoformat(timespec="seconds")
        )
        if not config.EMAIL_ENABLED:
            reset_token = token
            note = (
                "Email delivery is not configured on this server, so the reset "
                "link is shown here instead of being emailed."
            )
    return PasswordResetResponse(ok=True, reset_token=reset_token, note=note)


@router.post("/reset-password", response_model=PasswordResetResponse)
def reset_password(body: PasswordResetConfirm) -> PasswordResetResponse:
    token_hash = security.hash_token(body.token)
    user_id = db.get_password_reset_user_id(token_hash)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reset link is invalid or has expired. Request a new one.",
        )
    db.update_user_password(user_id, security.hash_password(body.password))
    db.delete_password_reset_token(token_hash)
    db.delete_user_sessions(user_id)  # log out everywhere after a reset
    return PasswordResetResponse(ok=True)


# --- Google sign-in (OAuth 2.0 authorization code flow) --------------------

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
OAUTH_STATE_COOKIE = "resume_oauth_state"
OAUTH_SIGNUP_CODE_COOKIE = "resume_oauth_signup_code"


def _decode_id_token(id_token: str) -> dict:
    """Decode (without signature verification) the claims of a Google
    ``id_token``. The token was just issued to us directly by Google's token
    endpoint over TLS, so trusting its claims here carries the same trust
    boundary as calling the userinfo endpoint would."""
    payload_b64 = id_token.split(".")[1]
    padded = payload_b64 + "=" * (-len(payload_b64) % 4)
    return json.loads(base64.urlsafe_b64decode(padded))


def _google_configured() -> bool:
    return bool(config.GOOGLE_CLIENT_ID and config.GOOGLE_CLIENT_SECRET)


def _google_redirect_uri() -> str:
    return f"{config.BACKEND_BASE_URL.rstrip('/')}/api/auth/google/callback"


@router.get("/google")
def google_start(signup_code: str | None = None) -> RedirectResponse:
    if not _google_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google sign-in is not configured on this server.",
        )
    state = secrets.token_urlsafe(24)
    params = urlencode(
        {
            "client_id": config.GOOGLE_CLIENT_ID,
            "redirect_uri": _google_redirect_uri(),
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "prompt": "select_account",
        }
    )
    response = RedirectResponse(url=f"{GOOGLE_AUTH_URL}?{params}", status_code=302)
    response.set_cookie(
        key=OAUTH_STATE_COOKIE,
        value=state,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite="lax",
        max_age=600,
        path="/",
    )
    if signup_code:
        # Carried through the redirect so the callback can gate first-time
        # sign-in the same way /register does; ignored for a returning user.
        response.set_cookie(
            key=OAUTH_SIGNUP_CODE_COOKIE,
            value=signup_code,
            httponly=True,
            secure=config.COOKIE_SECURE,
            samesite="lax",
            max_age=600,
            path="/",
        )
    return response


@router.get("/google/callback")
def google_callback(
    code: str | None = None,
    state: str | None = None,
    oauth_state: str | None = Cookie(default=None, alias=OAUTH_STATE_COOKIE),
    oauth_signup_code: str | None = Cookie(default=None, alias=OAUTH_SIGNUP_CODE_COOKIE),
) -> RedirectResponse:
    frontend = config.FRONTEND_URL.rstrip("/")

    def back_to_login(error: str) -> RedirectResponse:
        return RedirectResponse(url=f"{frontend}/login?error={error}", status_code=302)

    if not _google_configured():
        return back_to_login("google_unconfigured")
    if not code or not state or not oauth_state or state != oauth_state:
        return back_to_login("google_state")
    try:
        token_res = requests.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": config.GOOGLE_CLIENT_ID,
                "client_secret": config.GOOGLE_CLIENT_SECRET,
                "redirect_uri": _google_redirect_uri(),
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        token_res.raise_for_status()
        info = _decode_id_token(token_res.json()["id_token"])
    except Exception:
        return back_to_login("google_failed")

    google_id = info.get("sub")
    email = info.get("email")
    if not google_id or not email or info.get("email_verified") is False:
        return back_to_login("google_email")

    user = db.get_user_by_google_id(google_id)
    if user is None:
        existing = db.get_user_by_email(email)
        if existing:
            # Link the Google identity to the existing account.
            db.set_google_id(existing["id"], google_id)
            user = db.get_user_by_id(existing["id"])
        else:
            if config.SIGNUP_CODE and oauth_signup_code != config.SIGNUP_CODE:
                return back_to_login("signup_code")
            user_id = db.create_google_user(
                email, google_id, security.hash_password(secrets.token_urlsafe(32))
            )
            db.migrate_legacy_resumes_for_user(user_id)
            user = db.get_user_by_id(user_id)

    token = security.new_session_token()
    db.create_session(user["id"], token)
    response = RedirectResponse(url=f"{frontend}/profiles", status_code=302)
    _set_session_cookie(response, token)
    response.delete_cookie(OAUTH_STATE_COOKIE, path="/")
    response.delete_cookie(OAUTH_SIGNUP_CODE_COOKIE, path="/")
    return response
