from datetime import date

from fastapi import APIRouter, Query

from app.api.deps import DBSession
from app.schemas.discover import DiscoverQueryParams, DiscoverResponse
from app.services import discover_service


router = APIRouter(prefix="/discover", tags=["Discover"])


@router.get("", response_model=DiscoverResponse)
def get_discover(
    db: DBSession,
    category: str | None = Query(default=None),
    city: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    is_paid: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    trending_groups_page: int | None = Query(default=None, ge=1),
    trending_groups_page_size: int | None = Query(default=None, ge=1, le=50),
    upcoming_events_page: int | None = Query(default=None, ge=1),
    upcoming_events_page_size: int | None = Query(default=None, ge=1, le=50),
    nearby_events_page: int | None = Query(default=None, ge=1),
    nearby_events_page_size: int | None = Query(default=None, ge=1, le=50),
    new_groups_page: int | None = Query(default=None, ge=1),
    new_groups_page_size: int | None = Query(default=None, ge=1, le=50),
    trending_groups_sort: str = Query(default="default"),
    upcoming_events_sort: str = Query(default="soonest"),
    nearby_events_sort: str = Query(default="soonest"),
    new_groups_sort: str = Query(default="newest"),
) -> DiscoverResponse:
    params = DiscoverQueryParams(
        category=category,
        city=city,
        date_from=date_from,
        date_to=date_to,
        is_paid=is_paid,
        page=page,
        page_size=page_size,
        trending_groups_page=trending_groups_page,
        trending_groups_page_size=trending_groups_page_size,
        upcoming_events_page=upcoming_events_page,
        upcoming_events_page_size=upcoming_events_page_size,
        nearby_events_page=nearby_events_page,
        nearby_events_page_size=nearby_events_page_size,
        new_groups_page=new_groups_page,
        new_groups_page_size=new_groups_page_size,
        trending_groups_sort=trending_groups_sort,
        upcoming_events_sort=upcoming_events_sort,
        nearby_events_sort=nearby_events_sort,
        new_groups_sort=new_groups_sort,
    )
    return discover_service.get_discover_feed(db, params=params)
