from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GroupBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    cover_image_url: str | None = Field(default=None, max_length=2048)
    category: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)


class GroupCreate(GroupBase):
    pass


class GroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    cover_image_url: str | None = Field(default=None, max_length=2048)
    category: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)


class GroupRead(GroupBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    created_at: datetime
    updated_at: datetime


class GroupListResponse(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    member_count: int
    image_url: str | None = None


class GroupFounderResponse(BaseModel):
    id: UUID
    name: str


class GroupStatsResponse(BaseModel):
    posts: int = 0
    events: int = 0
    members: int = 0


class GroupEventPreviewResponse(BaseModel):
    id: UUID
    title: str
    starts_at: datetime


class GroupMemberPreviewResponse(BaseModel):
    id: UUID
    name: str
    avatar_url: str | None = None


class GroupDetailResponse(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    cover_image_url: str | None = None
    member_count: int
    is_joined: bool
    category: str | None = None
    location: str | None = None
    founder: GroupFounderResponse
    stats: GroupStatsResponse
    upcoming_events: list[GroupEventPreviewResponse] = Field(default_factory=list)
    gallery_preview: list[str] = Field(default_factory=list)
    member_preview: list[GroupMemberPreviewResponse] = Field(default_factory=list)


class GroupJoinResponse(BaseModel):
    success: bool


class GroupMemberResponse(BaseModel):
    id: UUID
    name: str
    avatar_url: str | None = None


class GroupMembershipMutationResponse(BaseModel):
    success: bool
    group_id: UUID
    is_joined: bool
    member_count: int
    action: str
