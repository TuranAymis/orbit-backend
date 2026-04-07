from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EventBase(BaseModel):
    group_id: UUID
    title: str = Field(..., min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    cover_image_url: str | None = Field(default=None, max_length=2048)
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
    cover_image_url: str | None = Field(default=None, max_length=2048)
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
    cover_image_url: str | None
    location: str
    start_time: datetime
    end_time: datetime
    created_at: datetime
    updated_at: datetime


class EventListResponse(BaseModel):
    id: UUID
    title: str
    description: str | None = None
    cover_image_url: str | None = None
    starts_at: datetime
    ends_at: datetime
    location: str
    attendee_count: int
    is_joined: bool


class EventRelatedGroupResponse(BaseModel):
    id: UUID
    name: str


class EventParticipantPreviewResponse(BaseModel):
    id: UUID
    name: str
    avatar_url: str | None = None


class EventDetailResponse(BaseModel):
    id: UUID
    title: str
    description: str | None = None
    cover_image_url: str | None = None
    starts_at: datetime
    ends_at: datetime
    location: str
    attendee_count: int
    is_joined: bool
    related_group: EventRelatedGroupResponse | None = None
    participants_preview: list[EventParticipantPreviewResponse] = Field(default_factory=list)


class EventJoinLeaveResponse(BaseModel):
    success: bool


class EventParticipantResponse(BaseModel):
    id: UUID
    name: str
    avatar_url: str | None = None


class EventAttendanceMutationResponse(BaseModel):
    success: bool
    event_id: UUID
    is_joined: bool
    attendee_count: int
    action: str
