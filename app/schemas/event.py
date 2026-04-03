from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EventBase(BaseModel):
    group_id: UUID
    title: str = Field(..., min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    location: str = Field(..., min_length=2, max_length=255)
    start_time: datetime
    end_time: datetime

    @model_validator(mode="after")
    def validate_times(self) -> Self:
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time.")
        return self


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    location: str | None = Field(default=None, min_length=2, max_length=255)
    start_time: datetime | None = None
    end_time: datetime | None = None

    @model_validator(mode="after")
    def validate_partial_times(self) -> Self:
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.end_time <= self.start_time
        ):
            raise ValueError("end_time must be after start_time.")
        return self


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    group_id: UUID
    title: str
    description: str | None
    location: str
    start_time: datetime
    end_time: datetime
    created_at: datetime
    updated_at: datetime
