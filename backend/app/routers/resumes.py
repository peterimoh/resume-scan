from __future__ import annotations

import base64
import json

from fastapi import APIRouter, Depends, HTTPException, Response, status

from .. import db
from ..deps import get_current_user, owned_profile, owned_resume
from ..resume_generator import (
    compile_pdf,
    pdf_to_png,
    pdf_to_pngs,
    render_tex,
)
from ..schemas import (
    ResumeCreate,
    ResumeData,
    ResumeOut,
    ResumePreviewRequest,
    ResumePreviewResponse,
    ResumeSummary,
    ResumeUpdate,
    resume_title,
    strip_uids,
)

router = APIRouter(tags=["resumes"])


def _resume_out(row: dict) -> ResumeOut:
    return ResumeOut(
        id=row["id"],
        profile_id=row["profile_id"],
        name=row["name"],
        template=row["template"],
        font=row["font"],
        data=ResumeData(**row["data"]),
        source=row.get("source", "built"),
        has_pdf=bool(row.get("pdf")),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("/api/profiles/{profile_id}/resumes", response_model=list[ResumeSummary])
def list_resumes(profile_id: int, user: dict = Depends(get_current_user)) -> list[dict]:
    owned_profile(profile_id, user)
    return db.list_resumes(profile_id)


@router.post(
    "/api/profiles/{profile_id}/resumes",
    response_model=ResumeOut,
    status_code=status.HTTP_201_CREATED,
)
def create_resume(
    profile_id: int, body: ResumeCreate, user: dict = Depends(get_current_user)
) -> ResumeOut:
    owned_profile(profile_id, user)
    data = body.data.cleaned()
    name = (body.name or "").strip() or resume_title(data)
    resume_id = db.create_resume(profile_id, name, body.template, body.font, data)
    return _resume_out(db.get_resume(resume_id))


@router.get("/api/resumes/{resume_id}", response_model=ResumeOut)
def get_resume(resume_id: int, user: dict = Depends(get_current_user)) -> ResumeOut:
    return _resume_out(owned_resume(resume_id, user))


@router.put("/api/resumes/{resume_id}", response_model=ResumeOut)
def update_resume(
    resume_id: int, body: ResumeUpdate, user: dict = Depends(get_current_user)
) -> ResumeOut:
    owned_resume(resume_id, user)
    data = body.data.cleaned()
    name = (body.name or "").strip() or resume_title(data)
    db.update_resume(resume_id, name, body.template, body.font, data)
    return _resume_out(db.get_resume(resume_id))


@router.delete("/api/resumes/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(resume_id: int, user: dict = Depends(get_current_user)) -> None:
    owned_resume(resume_id, user)
    db.delete_resume(resume_id)


@router.post(
    "/api/resumes/{resume_id}/duplicate",
    response_model=ResumeOut,
    status_code=status.HTTP_201_CREATED,
)
def duplicate_resume(resume_id: int, user: dict = Depends(get_current_user)) -> ResumeOut:
    owned_resume(resume_id, user)
    new_id = db.duplicate_resume(resume_id)
    return _resume_out(db.get_resume(new_id))


@router.post("/api/resumes/{resume_id}/pdf", response_model=ResumeOut)
def generate_pdf(resume_id: int, user: dict = Depends(get_current_user)) -> ResumeOut:
    resume = owned_resume(resume_id, user)
    try:
        tex = render_tex(resume["data"], resume["template"], resume["font"])
        pdf_bytes = compile_pdf(tex, jobname="resume")
    except Exception as exc:  # pdflatex failures, missing binaries, etc.
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    db.save_pdf(resume_id, pdf_bytes)
    return _resume_out(db.get_resume(resume_id))


@router.get("/api/resumes/{resume_id}/pdf")
def download_pdf(resume_id: int, user: dict = Depends(get_current_user)) -> Response:
    resume = owned_resume(resume_id, user)
    if not resume.get("pdf"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No PDF generated yet")
    filename = f"{resume_title(resume['data']).replace(' ', '_')}_{resume['template']}.pdf"
    return Response(
        content=resume["pdf"],
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/api/resumes/{resume_id}/json")
def download_json(resume_id: int, user: dict = Depends(get_current_user)) -> Response:
    resume = owned_resume(resume_id, user)
    cleaned = strip_uids(resume["data"])
    filename = f"{resume_title(cleaned).replace(' ', '_')}.json"
    return Response(
        content=json.dumps(cleaned, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/api/resumes/{resume_id}/thumbnail")
def thumbnail(resume_id: int, user: dict = Depends(get_current_user)) -> Response:
    resume = owned_resume(resume_id, user)
    if not resume.get("pdf"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No PDF generated yet")
    png = pdf_to_png(resume["pdf"], dpi=60)
    return Response(content=png, media_type="image/png")


@router.post("/api/resumes/preview", response_model=ResumePreviewResponse)
def preview(body: ResumePreviewRequest, user: dict = Depends(get_current_user)) -> ResumePreviewResponse:
    try:
        tex = render_tex(body.data.cleaned(), body.template, body.font)
        pdf_bytes = compile_pdf(tex, jobname=f"preview_{body.template}")
        pages = pdf_to_pngs(pdf_bytes, dpi=110)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return ResumePreviewResponse(
        pages=[f"data:image/png;base64,{base64.b64encode(p).decode()}" for p in pages]
    )
