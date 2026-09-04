from __future__ import annotations

from fastapi import APIRouter, Depends, status

from .. import db
from ..deps import get_current_user, owned_profile
from ..schemas import ProfileCreate, ProfileOut, ProfileUpdate

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


@router.get("", response_model=list[ProfileOut])
def list_profiles(user: dict = Depends(get_current_user)) -> list[dict]:
    return db.list_profiles(user["id"])


@router.post("", response_model=ProfileOut, status_code=status.HTTP_201_CREATED)
def create_profile(body: ProfileCreate, user: dict = Depends(get_current_user)) -> dict:
    profile_id = db.create_profile(user["id"], body.name, body.headline)
    return db.get_profile(profile_id)


@router.get("/{profile_id}", response_model=ProfileOut)
def get_profile(profile_id: int, user: dict = Depends(get_current_user)) -> dict:
    return owned_profile(profile_id, user)


@router.patch("/{profile_id}", response_model=ProfileOut)
def update_profile(profile_id: int, body: ProfileUpdate, user: dict = Depends(get_current_user)) -> dict:
    owned_profile(profile_id, user)
    db.update_profile(profile_id, body.name, body.headline)
    return db.get_profile(profile_id)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(profile_id: int, user: dict = Depends(get_current_user)) -> None:
    owned_profile(profile_id, user)
    db.delete_profile(profile_id)
