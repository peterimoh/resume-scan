"""FastAPI dependencies for auth and ownership checks."""

from __future__ import annotations

from fastapi import Cookie, Header, HTTPException, status

from . import config, db


def get_current_user(
    session_token: str | None = Cookie(default=None, alias=config.SESSION_COOKIE_NAME),
) -> dict:
    if session_token:
        user = db.get_session_user(session_token)
        if user:
            return user
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def owned_profile(profile_id: int, user: dict) -> dict:
    """Return the profile if it belongs to ``user``, else 404 (never 403 —
    do not confirm existence of another user's resources)."""
    profile = db.get_profile(profile_id)
    if profile is None or profile["user_id"] != user["id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile


def owned_resume(resume_id: int, user: dict) -> dict:
    """Return the resume (data parsed) if its profile belongs to ``user``,
    else 404."""
    resume = db.get_resume(resume_id)
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    owned_profile(resume["profile_id"], user)
    return resume


def owned_generation(generation_id: int, user: dict) -> dict:
    """Return the generation record if its resume belongs to ``user``, else
    404."""
    generation = db.get_generation(generation_id)
    if generation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    owned_resume(generation["resume_id"], user)
    return generation


def owned_job_subscription(subscription_id: int, user: dict) -> dict:
    subscription = db.get_job_subscription(subscription_id)
    if subscription is None or subscription["user_id"] != user["id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    return subscription


def require_internal_key(x_internal_key: str | None = Header(default=None)) -> None:
    """Guards /internal/* endpoints called by the n8n workflow. If
    INTERNAL_API_KEY is unset (local dev), the check is skipped — set it
    before exposing the backend publicly."""
    if config.INTERNAL_API_KEY and x_internal_key != config.INTERNAL_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal key")
