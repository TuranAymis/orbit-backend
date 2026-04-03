from fastapi import APIRouter

from app.api.deps import CurrentUser, DBSession
from app.crud import settings as settings_crud
from app.schemas.settings import SettingsResponse, SettingsUpdateRequest


router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("", response_model=SettingsResponse)
def read_settings(db: DBSession, current_user: CurrentUser) -> SettingsResponse:
    return settings_crud.get_or_create_settings(db, user=current_user)


@router.put("", response_model=SettingsResponse)
def update_settings(
    payload: SettingsUpdateRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> SettingsResponse:
    return settings_crud.update_settings(db, user=current_user, payload=payload)
