from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.event import Event
from app.models.event_participant import EventParticipant
from app.models.group import Group
from app.models.membership import Membership
from app.schemas.discover import (
    DiscoverEventGroupItem,
    DiscoverEventItem,
    DiscoverEventSection,
    DiscoverGroupItem,
    DiscoverGroupSection,
    DiscoverQueryParams,
    DiscoverResponse,
)


REMOTE_LOCATIONS = {"remote", "online", "virtual"}


@dataclass(frozen=True)
class PaginationSpec:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def _section_pagination(
    params: DiscoverQueryParams,
    *,
    prefix: str,
) -> PaginationSpec:
    page = getattr(params, f"{prefix}_page") or params.page
    page_size = getattr(params, f"{prefix}_page_size") or params.page_size
    return PaginationSpec(page=page, page_size=page_size)


def _has_more(*, total: int, pagination: PaginationSpec) -> bool:
    return total > pagination.offset + pagination.page_size


def _normalize_city(location: str | None, *, requested_city: str | None = None) -> str | None:
    if requested_city:
        return requested_city.strip()

    if location is None:
        return None

    normalized_location = location.strip()
    if not normalized_location:
        return None

    if normalized_location.lower() in REMOTE_LOCATIONS:
        return None

    if "," in normalized_location:
        return normalized_location.split(",")[-1].strip()

    return normalized_location


def _build_group_base_query(
    *,
    category: str | None,
    city: str | None,
) -> Select:
    member_counts = (
        select(
            Membership.group_id.label("group_id"),
            func.count(Membership.id).label("member_count"),
        )
        .group_by(Membership.group_id)
        .subquery()
    )
    event_counts = (
        select(
            Event.group_id.label("group_id"),
            func.count(Event.id).label("event_count"),
        )
        .group_by(Event.group_id)
        .subquery()
    )

    stmt = (
        select(
            Group,
            func.coalesce(member_counts.c.member_count, 0).label("member_count"),
            func.coalesce(event_counts.c.event_count, 0).label("event_count"),
        )
        .outerjoin(member_counts, member_counts.c.group_id == Group.id)
        .outerjoin(event_counts, event_counts.c.group_id == Group.id)
    )

    if category:
        stmt = stmt.where(Group.category == category.strip())
    if city:
        stmt = stmt.where(Group.location.ilike(f"%{city.strip()}%"))

    return stmt


def _build_event_base_query(
    *,
    category: str | None,
    city: str | None,
    date_from: date | None,
    date_to: date | None,
    upcoming_only: bool,
    nearby_only: bool,
) -> Select:
    attendee_counts = (
        select(
            EventParticipant.event_id.label("event_id"),
            func.count().label("attendee_count"),
        )
        .group_by(EventParticipant.event_id)
        .subquery()
    )

    stmt = (
        select(
            Event,
            Group,
            func.coalesce(attendee_counts.c.attendee_count, 0).label("attendee_count"),
        )
        .join(Group, Group.id == Event.group_id)
        .outerjoin(attendee_counts, attendee_counts.c.event_id == Event.id)
    )

    if category:
        stmt = stmt.where(Group.category == category.strip())

    if date_from:
        stmt = stmt.where(
            Event.start_time >= datetime.combine(date_from, time.min, tzinfo=UTC)
        )

    if date_to:
        stmt = stmt.where(
            Event.start_time <= datetime.combine(date_to, time.max, tzinfo=UTC)
        )

    if upcoming_only:
        stmt = stmt.where(Event.start_time >= datetime.now(UTC))

    if nearby_only:
        if city:
            city_value = city.strip()
            stmt = stmt.where(
                Group.location.ilike(f"%{city_value}%") | Event.location.ilike(f"%{city_value}%")
            )
        else:
            stmt = stmt.where(False)
    elif city:
        city_value = city.strip()
        stmt = stmt.where(
            Group.location.ilike(f"%{city_value}%") | Event.location.ilike(f"%{city_value}%")
        )

    return stmt


def _paginate(stmt: Select, *, pagination: PaginationSpec) -> Select:
    return stmt.offset(pagination.offset).limit(pagination.page_size)


def _count_rows(db: Session, stmt: Select) -> int:
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    return int(db.scalar(count_stmt) or 0)


def _resolve_group_section(
    db: Session,
    *,
    params: DiscoverQueryParams,
    section: str,
) -> DiscoverGroupSection:
    pagination = _section_pagination(params, prefix=section)
    base_stmt = _build_group_base_query(category=params.category, city=params.city)

    if section == "trending_groups":
        if params.trending_groups_sort == "newest":
            ordered_stmt = base_stmt.order_by(Group.created_at.desc())
        elif params.trending_groups_sort == "members":
            ordered_stmt = base_stmt.order_by(
                base_stmt.selected_columns.member_count.desc(),
                Group.created_at.desc(),
            )
        else:
            ordered_stmt = base_stmt.order_by(
                base_stmt.selected_columns.member_count.desc(),
                base_stmt.selected_columns.event_count.desc(),
                Group.created_at.desc(),
            )
    else:
        if params.new_groups_sort == "members":
            ordered_stmt = base_stmt.order_by(
                base_stmt.selected_columns.member_count.desc(),
                Group.created_at.desc(),
            )
        else:
            ordered_stmt = base_stmt.order_by(Group.created_at.desc())

    total = _count_rows(db, ordered_stmt)
    rows = db.execute(_paginate(ordered_stmt, pagination=pagination)).all()

    items = [
        DiscoverGroupItem(
            id=group.id,
            name=group.name,
            description=group.description,
            image_url=group.cover_image_url,
            member_count=int(member_count or 0),
            category=group.category,
            city=_normalize_city(group.location, requested_city=params.city if params.city else None),
        )
        for group, member_count, _event_count in rows
    ]

    return DiscoverGroupSection(
        items=items,
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
        has_more=_has_more(total=total, pagination=pagination),
    )


def _resolve_event_section(
    db: Session,
    *,
    params: DiscoverQueryParams,
    section: str,
) -> DiscoverEventSection:
    pagination = _section_pagination(params, prefix=section)
    nearby_only = section == "nearby_events"
    base_stmt = _build_event_base_query(
        category=params.category,
        city=params.city,
        date_from=params.date_from,
        date_to=params.date_to,
        upcoming_only=True,
        nearby_only=nearby_only,
    )

    sort_value = (
        params.nearby_events_sort if nearby_only else params.upcoming_events_sort
    )
    ordered_stmt = (
        base_stmt.order_by(Event.start_time.desc(), Event.created_at.desc())
        if sort_value == "latest"
        else base_stmt.order_by(Event.start_time.asc(), Event.created_at.desc())
    )

    total = _count_rows(db, ordered_stmt)
    rows = db.execute(_paginate(ordered_stmt, pagination=pagination)).all()

    items = [
        DiscoverEventItem(
            id=event.id,
            title=event.title,
            description=event.description,
            cover_image_url=event.cover_image_url,
            starts_at=event.start_time,
            ends_at=event.end_time,
            location=event.location,
            city=_normalize_city(
                event.location,
                requested_city=params.city if nearby_only and params.city else None,
            )
            or _normalize_city(group.location),
            attendee_count=int(attendee_count or 0),
            group=DiscoverEventGroupItem(id=group.id, name=group.name),
        )
        for event, group, attendee_count in rows
    ]

    return DiscoverEventSection(
        items=items,
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
        has_more=_has_more(total=total, pagination=pagination),
    )


def get_discover_feed(db: Session, *, params: DiscoverQueryParams) -> DiscoverResponse:
    if params.is_paid is not None:
        raise AppException("The is_paid filter is not supported yet for discover.")

    return DiscoverResponse(
        trending_groups=_resolve_group_section(
            db,
            params=params,
            section="trending_groups",
        ),
        upcoming_events=_resolve_event_section(
            db,
            params=params,
            section="upcoming_events",
        ),
        nearby_events=_resolve_event_section(
            db,
            params=params,
            section="nearby_events",
        ),
        new_groups=_resolve_group_section(
            db,
            params=params,
            section="new_groups",
        ),
    )
