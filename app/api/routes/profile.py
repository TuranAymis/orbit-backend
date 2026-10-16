from fastapi import APIRouter

from app.api.deps import CurrentUser, DBSession
from app.crud import user as user_crud
from app.schemas.user import ProfileResponse, ProfileUpdateRequest
from app.services.badge_service import evaluate_badges_best_effort


router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("", response_model=ProfileResponse)
def read_profile(current_user: CurrentUser) -> ProfileResponse:
    return current_user


@router.put("", response_model=ProfileResponse)
def update_profile(
    payload: ProfileUpdateRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> ProfileResponse:
    user = user_crud.update_user_profile(
        db,
        user=current_user,
        full_name=payload.full_name,
        bio=payload.bio,
        location=payload.location,
        avatar_url=payload.avatar_url,
    )
    evaluate_badges_best_effort(db, current_user.id)
    return user
