from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import get_current_user
from ..resume_generator import FONTS, TEMPLATES, installed_fonts

router = APIRouter(prefix="/api/meta", tags=["meta"])


@router.get("/templates")
def list_templates(user: dict = Depends(get_current_user)) -> dict:
    return {key: {"label": label, "description": desc} for key, (label, desc) in TEMPLATES.items()}


@router.get("/fonts")
def list_fonts(user: dict = Depends(get_current_user)) -> dict:
    available = set(installed_fonts())
    return {
        key: {"label": label, "available": key in available}
        for key, (label, _preamble) in FONTS.items()
    }
