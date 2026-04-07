from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


DiscoverGroupSort = Literal["default", "members", "newest"]
DiscoverEventSort = Literal["soonest", "latest"]


class DiscoverPaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    has_more: bool


class DiscoverSection(BaseModel):
    page: int
    page_size: int
    total: int
    has_more: bool


class DiscoverGroupItem(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    image_url: str | None = None
    member_count: int
    category: str | None = None
    city: str | None = None


class DiscoverEventGroupItem(BaseModel):
    id: UUID
    name: str


class DiscoverEventItem(BaseModel):
    id: UUID
    title: str
    description: str | None = None
    cover_image_url: str | None = None
    starts_at: datetime
    ends_at: datetime
    location: str
    city: str | None = None
    attendee_count: int
    group: DiscoverEventGroupItem


class DiscoverGroupSection(DiscoverSection):
    items: list[DiscoverGroupItem] = Field(default_factory=list)


class DiscoverEventSection(DiscoverSection):
    items: list[DiscoverEventItem] = Field(default_factory=list)


class DiscoverResponse(BaseModel):
    trending_groups: DiscoverGroupSection
    upcoming_events: DiscoverEventSection
    nearby_events: DiscoverEventSection
    new_groups: DiscoverGroupSection


class DiscoverQueryParams(BaseModel):
    category: str | None = None
    city: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=50)
    trending_groups_page: int | None = Field(default=None, ge=1)
    trending_groups_page_size: int | None = Field(default=None, ge=1, le=50)
    upcoming_events_page: int | None = Field(default=None, ge=1)
    upcoming_events_page_size: int | None = Field(default=None, ge=1, le=50)
    nearby_events_page: int | None = Field(default=None, ge=1)
    nearby_events_page_size: int | None = Field(default=None, ge=1, le=50)
    new_groups_page: int | None = Field(default=None, ge=1)
    new_groups_page_size: int | None = Field(default=None, ge=1, le=50)
    trending_groups_sort: DiscoverGroupSort = "default"
    upcoming_events_sort: DiscoverEventSort = "soonest"
    nearby_events_sort: DiscoverEventSort = "soonest"
    new_groups_sort: Literal["newest", "members"] = "newest"
    is_paid: bool | None = None

    @model_validator(mode="after")
    def validate_date_range(self) -> "DiscoverQueryParams":
        if (
            self.date_from is not None
            and self.date_to is not None
            and self.date_to < self.date_from
        ):
            raise ValueError("date_to must be on or after date_from.")
        return self
