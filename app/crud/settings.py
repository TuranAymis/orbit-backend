from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_settings import UserSettings
from app.schemas.settings import SettingsUpdateRequest


DEFAULT_SETTINGS = {
    "email_notifications": True,
    "push_notifications": False,
    "marketing_emails": False,
    "profile_visibility": "public",
    "theme_preference": "dark",
    "language": "en",
}


def get_or_create_settings(db: Session, *, user: User) -> UserSettings:
    settings = user.settings
    if settings is not None:
        return settings

    settings = UserSettings(user_id=user.id, **DEFAULT_SETTINGS)
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def update_settings(
    db: Session,
    *,
    user: User,
    payload: SettingsUpdateRequest,
) -> UserSettings:
    settings = get_or_create_settings(db, user=user)
    settings.email_notifications = payload.email_notifications
    settings.push_notifications = payload.push_notifications
    settings.marketing_emails = payload.marketing_emails
    settings.profile_visibility = payload.profile_visibility
    settings.theme_preference = payload.theme_preference
    settings.language = payload.language.strip().lower()

    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings
