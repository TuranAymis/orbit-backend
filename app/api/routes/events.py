from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, DBSession
from app.core.exceptions import AuthorizationError
from app.crud import event as event_crud
from app.crud import group as group_crud
from app.crud import membership as membership_crud
from app.models.user import User
from app.schemas.event import EventCreate, EventRead, EventUpdate
from app.utils.enums import MembershipRole, MembershipStatus


router = APIRouter(prefix="/events", tags=["Events"])


def _ensure_group_manager(db: Session, group_id: UUID, current_user: User) -> None:
    group = group_crud.get_group(db, group_id)
    if group.owner_id == current_user.id:
        return

    membership = membership_crud.get_membership_by_user_group(
        db,
        user_id=current_user.id,
        group_id=group_id,
    )
    if membership is None:
        raise AuthorizationError("You must be a group owner or admin to manage events.")
    if membership.status != MembershipStatus.ACTIVE:
        raise AuthorizationError("Only active group members can manage events.")
    if membership.role not in {MembershipRole.ADMIN, MembershipRole.OWNER}:
        raise AuthorizationError("You must be a group owner or admin to manage events.")


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
def create_event(
    payload: EventCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> EventRead:
    _ensure_group_manager(db, payload.group_id, current_user)
    return event_crud.create_event(
        db,
        group_id=payload.group_id,
        title=payload.title,
        description=payload.description,
        location=payload.location,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )


@router.get("", response_model=list[EventRead])
def list_events(
    db: DBSession,
    group_id: UUID | None = Query(default=None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> list[EventRead]:
    return event_crud.list_events(db, group_id=group_id, skip=skip, limit=limit)


@router.get("/{event_id}", response_model=EventRead)
def get_event(event_id: UUID, db: DBSession) -> EventRead:
    return event_crud.get_event(db, event_id)


@router.put("/{event_id}", response_model=EventRead)
def update_event(
    event_id: UUID,
    payload: EventUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> EventRead:
    event = event_crud.get_event(db, event_id)
    _ensure_group_manager(db, event.group_id, current_user)

    update_data = payload.model_dump(exclude_unset=True)
    resolved_start_time = update_data.get("start_time", event.start_time)
    resolved_end_time = update_data.get("end_time", event.end_time)
    if resolved_end_time <= resolved_start_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_time must be after start_time.",
        )

    return event_crud.update_event(db, db_obj=event, update_data=update_data)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> Response:
    event = event_crud.get_event(db, event_id)
    _ensure_group_manager(db, event.group_id, current_user)
    event_crud.delete_event(db, db_obj=event)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
