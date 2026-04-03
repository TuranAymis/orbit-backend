from pydantic import BaseModel, ConfigDict, Field


class SettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email_notifications: bool = True
    push_notifications: bool = False
    marketing_emails: bool = False
    profile_visibility: str = "public"
    theme_preference: str = "dark"
    language: str = "en"


class SettingsUpdateRequest(BaseModel):
    email_notifications: bool
    push_notifications: bool
    marketing_emails: bool
    profile_visibility: str = Field(..., pattern="^(public|private)$")
    theme_preference: str = Field(..., pattern="^(dark|light|system)$")
    language: str = Field(..., min_length=2, max_length=10)
