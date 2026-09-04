from __future__ import annotations

import json
from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse

from .. import db, llm, report_generator
from ..deps import get_current_user, owned_generation, owned_resume
from ..resume_generator import compile_pdf, pdf_to_text, render_tex
from ..schemas import (
    AnalysisPdfRequest,
    AnalysisRequest,
    GenerationOut,
    GenerationSummary,
    HistoryEntry,
)

router = APIRouter(tags=["analysis"])


def _resume_text(resume: dict) -> str:
    pdf_bytes = resume.get("pdf")
    if not pdf_bytes:
        tex = render_tex(resume["data"], resume["template"], resume["font"])
        pdf_bytes = compile_pdf(tex, jobname="resume")
    return pdf_to_text(pdf_bytes)


def _sse_stream(chunks, on_complete: Callable[[str], None] | None = None):
    acc: list[str] = []
    for chunk in chunks:
        acc.append(chunk)
        yield f"data: {json.dumps(chunk)}\n\n"
    # Only reached if the loop above completed normally — a client
    # disconnect raises GeneratorExit at the yield above and unwinds the
    # generator without running this, so aborted runs are never persisted.
    if on_complete:
        on_complete("".join(acc))
    yield "event: done\ndata: {}\n\n"


def _run_generation(
    resume_id: int, body: AnalysisRequest, user: dict, kind: str, generator_fn
) -> StreamingResponse:
    resume = owned_resume(resume_id, user)
    try:
        text = _resume_text(resume)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    def on_complete(full_text: str) -> None:
        db.create_generation(resume_id, kind, body.job_description, full_text)

    return StreamingResponse(
        _sse_stream(generator_fn(text, body.job_description), on_complete=on_complete),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/api/resumes/{resume_id}/analysis/hr")
def analyze_hr(resume_id: int, body: AnalysisRequest, user: dict = Depends(get_current_user)) -> StreamingResponse:
    return _run_generation(resume_id, body, user, "hr", llm.analyze_hr)


@router.post("/api/resumes/{resume_id}/analysis/ats")
def analyze_ats(resume_id: int, body: AnalysisRequest, user: dict = Depends(get_current_user)) -> StreamingResponse:
    return _run_generation(resume_id, body, user, "ats", llm.analyze_ats)


@router.post("/api/resumes/{resume_id}/analysis/cover-letter")
def generate_cover_letter(
    resume_id: int, body: AnalysisRequest, user: dict = Depends(get_current_user)
) -> StreamingResponse:
    return _run_generation(resume_id, body, user, "cover_letter", llm.generate_cover_letter)


@router.get("/api/history", response_model=list[HistoryEntry])
def list_all_history(kind: str | None = None, user: dict = Depends(get_current_user)) -> list[dict]:
    """Every HR/ATS/cover-letter run for the current user, across every
    profile and Quick Check scans, for the unified History page."""
    rows = db.list_all_generations(user["id"], kind)
    for row in rows:
        row["is_quick"] = row.pop("profile_kind") == "quick"
    return rows


@router.get("/api/resumes/{resume_id}/history", response_model=list[GenerationSummary])
def list_history(
    resume_id: int, kind: str | None = None, user: dict = Depends(get_current_user)
) -> list[dict]:
    owned_resume(resume_id, user)
    return db.list_generations(resume_id, kind)


@router.post("/api/resumes/{resume_id}/analysis/pdf")
def download_analysis_pdf(
    resume_id: int, body: AnalysisPdfRequest, user: dict = Depends(get_current_user)
) -> Response:
    """Render an HR review or ATS check (as currently shown on screen, or a
    saved history record) into a formatted PDF. Takes the result text
    directly rather than a generation id so this works right after a run
    completes, before the page has reloaded history."""
    if body.kind not in ("hr", "ats"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDF export supports HR review and ATS check only.",
        )
    resume = owned_resume(resume_id, user)
    try:
        pdf_bytes = report_generator.render_analysis_pdf(
            kind=body.kind,
            resume_name=resume["name"],
            job_description=body.job_description,
            raw_result=body.result,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    label = "ATS_Check" if body.kind == "ats" else "HR_Review"
    safe_name = resume["name"].replace(" ", "_")
    filename = f"{label}_{safe_name}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/api/history/{generation_id}", response_model=GenerationOut)
def get_history_record(generation_id: int, user: dict = Depends(get_current_user)) -> dict:
    return owned_generation(generation_id, user)


@router.delete("/api/history/{generation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_history_record(generation_id: int, user: dict = Depends(get_current_user)) -> None:
    owned_generation(generation_id, user)
    db.delete_generation(generation_id)
