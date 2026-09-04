"""Profile-less "Quick Check" flow: upload an existing resume PDF directly
and run ATS/HR analysis on it without ever creating a Profile.

Uploads are stored under a hidden, auto-created "Quick Scans" profile (see
db.get_or_create_quick_profile) so every other endpoint — analysis, history,
delete, PDF download — works unchanged via the normal ownership chain.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status

from .. import db
from ..deps import get_current_user
from ..schemas import ResumeOut, ResumeSummary
from .resumes import _resume_out

router = APIRouter(prefix="/api/quick-resumes", tags=["quick"])

MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB


@router.get("", response_model=list[ResumeSummary])
def list_quick_resumes(user: dict = Depends(get_current_user)) -> list[dict]:
    profile_id = db.find_quick_profile(user["id"])
    if profile_id is None:
        return []
    return db.list_resumes(profile_id)


@router.post("", response_model=ResumeOut, status_code=status.HTTP_201_CREATED)
async def upload_quick_resume(
    file: UploadFile = File(...), user: dict = Depends(get_current_user)
) -> ResumeOut:
    filename = file.filename or "Uploaded resume"
    if file.content_type != "application/pdf" and not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Please upload a PDF file."
        )
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File is too large (max 8 MB).",
        )
    if not data.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That file doesn't look like a valid PDF.",
        )
    profile_id = db.get_or_create_quick_profile(user["id"])
    name = filename.rsplit(".", 1)[0].strip()[:200] or "Uploaded resume"
    resume_id = db.create_uploaded_resume(profile_id, name, data)
    return _resume_out(db.get_resume(resume_id))
