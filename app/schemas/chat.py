from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ChatCreate(BaseModel):
    group_id: UUID | None = None
    event_id: UUID | None = None
    message: str = Field(..., min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("Message cannot be empty.")
        return stripped_value

    @model_validator(mode="after")
    def validate_context(self) -> Self:
        if self.group_id is None and self.event_id is None:
            raise ValueError("Either group_id or event_id must be provided.")
        return self


class ChatRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sender_id: UUID
    group_id: UUID | None
    event_id: UUID | None
    message: str
    created_at: datetime
