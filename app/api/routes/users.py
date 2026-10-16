from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.models.user_badge import UserBadge
from app.schemas.badge import BadgeResponse
from app.schemas.user import UserMeResponse
from app.services.badge_service import BADGE_RULES


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserMeResponse)
def read_current_user(current_user: CurrentUser) -> UserMeResponse:
    return current_user


@router.get("/me/badges", response_model=list[BadgeResponse])
def read_my_badges(db: DBSession, current_user: CurrentUser) -> list[BadgeResponse]:
    earned = {
        badge.badge_key: badge.awarded_at
        for badge in db.scalars(select(UserBadge).where(UserBadge.user_id == current_user.id))
    }
    return [
        BadgeResponse(
            key=rule.key,
            title=rule.title,
            description=rule.description,
            earned=rule.key in earned,
            awarded_at=earned.get(rule.key),
        )
        for rule in BADGE_RULES
    ]
