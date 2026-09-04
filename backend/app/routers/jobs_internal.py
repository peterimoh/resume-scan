"""Internal endpoints called by the n8n job-board workflow, not the
frontend. Every route requires the X-Internal-Key header (see
deps.require_internal_key) instead of a user session.

Keeping ingestion/matching/dedup logic here — rather than in n8n's Function
nodes — means it's covered by the same DB layer as the rest of the app and
can be unit tested without touching the workflow.
"""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends

from .. import db
from ..deps import require_internal_key
from ..schemas import (
    JobMatchRequest,
    JobMatchResponse,
    JobNotificationRecordRequest,
    JobNotificationRecordResponse,
    JobUpsertBatchRequest,
    JobUpsertBatchResponse,
)

router = APIRouter(prefix="/internal", tags=["internal"], dependencies=[Depends(require_internal_key)])


def _dedup_hash(source: str, title: str, company: str | None, dedup_ident: str) -> str:
    # dedup_ident is normally the url (usually unique per posting); title+
    # company is folded in too so re-posts under a slightly different query
    # string still collapse to one row. Sources whose url isn't stable
    # across requests (e.g. a per-request tracking redirect) send a
    # dedup_key instead — see JobPostingIn.
    key = f"{source}|{title.strip().lower()}|{(company or '').strip().lower()}|{dedup_ident.strip().lower()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


@router.post("/jobs/upsert-batch", response_model=JobUpsertBatchResponse)
def upsert_jobs(body: JobUpsertBatchRequest) -> dict:
    postings = []
    for p in body.postings:
        title = db.clean_text(p.title)
        company = db.clean_text(p.company)
        postings.append(
            {
                "dedup_hash": _dedup_hash(p.source, title, company, p.dedup_key or p.url),
                "source": p.source,
                "title": title,
                "company": company,
                "location": db.clean_text(p.location),
                "job_type": db.clean_text(p.job_type),
                "salary": db.clean_text(p.salary),
                "description": db.clean_text(p.description),
                "url": p.url,
                "posted_at": p.posted_at,
            }
        )
    inserted = db.upsert_jobs(postings)
    return {"inserted": inserted}


@router.get("/subscriptions/active", response_model=list[dict])
def active_subscriptions() -> list[dict]:
    return db.list_active_job_subscriptions()


@router.post("/jobs/match", response_model=JobMatchResponse)
def match_jobs(body: JobMatchRequest) -> dict:
    """Case-insensitive substring match of each active subscription's
    keyword against each candidate job's title. Deliberately simple for a
    first cut — swap in fuzzy/embedding matching here later without
    touching the n8n workflow."""
    subscriptions = db.list_active_job_subscriptions()
    matches: list[dict] = []
    for job_id in body.job_ids:
        job = db.get_job(job_id)
        if job is None:
            continue
        title = job["title"].lower()
        for sub in subscriptions:
            if sub["keyword"].strip().lower() in title:
                matches.append(
                    {
                        "subscription_id": sub["id"],
                        "user_id": sub["user_id"],
                        "job_id": job_id,
                        "channel": sub["channel"],
                        "channel_target": sub["channel_target"],
                        "job_title": job["title"],
                        "job_company": job["company"],
                        "job_location": job["location"],
                        "job_type": job["job_type"],
                        "job_salary": job["salary"],
                        "job_url": job["url"],
                    }
                )
    return {"matches": matches}


@router.post("/notifications/record", response_model=JobNotificationRecordResponse)
def record_notification(body: JobNotificationRecordRequest) -> dict:
    recorded = db.record_job_notification(
        body.user_id, body.job_id, body.subscription_id, body.channel, body.status
    )
    return {"recorded": recorded}
