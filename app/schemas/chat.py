from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ChatCreate(BaseModel):
    group_id: UUID | None = None
    event_id: UUID | None = None
    content: str = Field(..., min_length=1, max_length=4000)

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("content cannot be empty.")
        return stripped_value

    @model_validator(mode="after")
    def validate_context(self) -> Self:
        if self.group_id is None and self.event_id is None:
            raise ValueError("Either group_id or event_id must be provided.")
        return self


class ChatRead(BaseModel):
    id: UUID
    group_id: UUID | None = None
    user_id: UUID
    username: str
    content: str
    created_at: datetime


class ChatSeedMessage(BaseModel):
    group_id: UUID | None
    event_id: UUID | None
    user_id: UUID
    content: str
