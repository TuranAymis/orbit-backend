from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.schemas.user import UserMeResponse


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserMeResponse)
def read_current_user(current_user: CurrentUser) -> UserMeResponse:
    return current_user
