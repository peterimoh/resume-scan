"""User-facing job board: manage keyword/channel subscriptions and read the
matched-jobs feed. Ingestion, matching and notification delivery happen out
of process in n8n, via the internal endpoints in ``jobs_internal.py``."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, status

from .. import db
from ..deps import get_current_user, owned_job_subscription
from ..schemas import (
    JobFilterOptions,
    JobListResponse,
    JobNotificationOut,
    JobOut,
    JobSubscriptionCreate,
    JobSubscriptionOut,
)

router = APIRouter(prefix="/api/job-subscriptions", tags=["jobs"])
feed_router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", response_model=list[JobSubscriptionOut])
def list_subscriptions(user: dict = Depends(get_current_user)) -> list[dict]:
    return db.list_job_subscriptions(user["id"])


@router.post("", response_model=JobSubscriptionOut, status_code=status.HTTP_201_CREATED)
def create_subscription(
    body: JobSubscriptionCreate, user: dict = Depends(get_current_user)
) -> dict:
    channel_target = body.channel_target.strip()
    if body.channel == "telegram":
        # channel_target must be the user's own verified chat_id — never a
        # freely-typed value — so notifications can't be redirected to a
        # chat the user doesn't actually control.
        link = db.get_telegram_link(user["id"])
        if link is None or link["chat_id"] != channel_target:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Connect your Telegram account before subscribing on Telegram.",
            )
    subscription_id = db.create_job_subscription(
        user["id"], body.keyword.strip(), body.channel, channel_target
    )
    return db.get_job_subscription(subscription_id)


@router.patch("/{subscription_id}/pause", response_model=JobSubscriptionOut)
def pause_subscription(subscription_id: int, user: dict = Depends(get_current_user)) -> dict:
    owned_job_subscription(subscription_id, user)
    db.set_job_subscription_active(subscription_id, False)
    return db.get_job_subscription(subscription_id)


@router.patch("/{subscription_id}/resume", response_model=JobSubscriptionOut)
def resume_subscription(subscription_id: int, user: dict = Depends(get_current_user)) -> dict:
    owned_job_subscription(subscription_id, user)
    db.set_job_subscription_active(subscription_id, True)
    return db.get_job_subscription(subscription_id)


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(subscription_id: int, user: dict = Depends(get_current_user)) -> None:
    owned_job_subscription(subscription_id, user)
    db.delete_job_subscription(subscription_id)


@feed_router.get("/feed", response_model=list[JobNotificationOut])
def job_feed(user: dict = Depends(get_current_user)) -> list[dict]:
    """Every job this user has been matched + notified on, newest first —
    populated regardless of whether the external channel delivery
    succeeded, so nothing is lost if e.g. a WhatsApp send fails."""
    return db.list_job_notifications(user["id"])


@feed_router.get("/filter-options", response_model=JobFilterOptions)
def job_filter_options(user: dict = Depends(get_current_user)) -> dict:
    """Distinct job_type/source values actually present, so the frontend
    can render filter dropdowns instead of asking users to guess values."""
    return db.list_job_filter_options()


# Posted-at filter shorthand accepted by the browse endpoint: e.g. "24h", "3d", "2w".
_POSTED_WITHIN_RE = re.compile(r"^(\d+)([hdw])$")

_POSTED_WITHIN_UNITS = {"h": 1, "d": 24, "w": 24 * 7}


def _posted_within_hours(value: str) -> int:
    match = _POSTED_WITHIN_RE.match(value.strip().lower())
    if not match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="posted_within must look like '24h', '3d' or '2w'.",
        )
    amount, unit = match.groups()
    hours = int(amount) * _POSTED_WITHIN_UNITS[unit]
    if hours < 1 or hours > 24 * 366:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="posted_within is out of range.",
        )
    return hours


@feed_router.get("", response_model=JobListResponse)
def browse_jobs(
    q: str | None = None,
    location: str | None = None,
    job_type: str | None = None,
    source: str | None = None,
    posted_within: str | None = None,
    page: int = 1,
    page_size: int = 20,
    user: dict = Depends(get_current_user),
) -> dict:
    """Browse the full ingested job pool, not just this user's matches."""
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    items, total = db.list_jobs(
        q=q,
        location=location,
        job_type=job_type,
        source=source,
        posted_within_hours=_posted_within_hours(posted_within) if posted_within else None,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@feed_router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, user: dict = Depends(get_current_user)) -> dict:
    job = db.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job
