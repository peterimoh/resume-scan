from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import config, db
from .routers import analysis, auth, jobs, jobs_internal, meta, profiles, quick, resumes, telegram

app = FastAPI(title="Resume Builder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profiles.router)
app.include_router(resumes.router)
app.include_router(quick.router)
app.include_router(meta.router)
app.include_router(analysis.router)
app.include_router(jobs.router)
app.include_router(jobs.feed_router)
app.include_router(jobs_internal.router)
app.include_router(telegram.router)


@app.on_event("startup")
def on_startup() -> None:
    db.init_db()
    db.seed_legacy_json_if_empty()


def _sanitize_errors(value):
    """Recursively repair unpaired UTF-16 surrogates in a validation-error
    payload. Pydantic can reject a request body containing one (e.g. an
    emoji truncated mid-codepoint by an upstream source) with the offending
    value echoed back in the error detail — and the default error handler
    then crashes trying to UTF-8-encode that same value into the response.
    Sanitizing here keeps that a clean 422 instead of an opaque 500."""
    if isinstance(value, str):
        return db.clean_text(value)
    if isinstance(value, dict):
        return {k: _sanitize_errors(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_errors(v) for v in value]
    return value


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": _sanitize_errors(exc.errors())})


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}
