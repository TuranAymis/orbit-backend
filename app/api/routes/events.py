from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentAdmin, CurrentUser, DBSession, OptionalCurrentUser
from app.core.exceptions import AuthorizationError
from app.crud import event as event_crud
from app.crud import event_moderator as event_moderator_crud
from app.crud import group as group_crud
from app.crud import group_moderator as group_moderator_crud
from app.crud import membership as membership_crud
from app.crud import user as user_crud
from app.models.user import User
from app.schemas.event import (
    EventCreate,
    EventDetailResponse,
    EventJoinLeaveResponse,
    EventListResponse,
    EventParticipantPreviewResponse,
    EventParticipantResponse,
    EventRead,
    EventRelatedGroupResponse,
    EventUpdate,
)
from app.utils.enums import MembershipRole, MembershipStatus, UserRole


router = APIRouter(prefix="/events", tags=["Events"])


def _ensure_event_creator(db: Session, group_id: UUID, current_user: User) -> None:
    group_crud.get_group(db, group_id)

    if current_user.role == UserRole.ADMIN:
        return

    if current_user.role == UserRole.MODERATOR:
        if group_moderator_crud.get_group_moderator(
            db,
            group_id=group_id,
            user_id=current_user.id,
        ) is not None:
            return

        raise AuthorizationError(
            "You must be assigned as a moderator for this group to create events."
        )

    raise AuthorizationError("Moderator or admin access is required to create events.")


def _ensure_group_manager(db: Session, group_id: UUID, current_user: User) -> None:
    if current_user.role in {UserRole.MODERATOR, UserRole.ADMIN}:
        return

    if group_moderator_crud.get_group_moderator(
        db,
        group_id=group_id,
        user_id=current_user.id,
    ) is not None:
        return

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


def _ensure_event_deleter(db: Session, event_id: UUID, current_user: User) -> None:
    event = event_crud.get_event(db, event_id)

    if current_user.role == UserRole.ADMIN:
        return

    if current_user.role == UserRole.MODERATOR:
        if group_moderator_crud.get_group_moderator(
            db,
            group_id=event.group_id,
            user_id=current_user.id,
        ) is not None:
            return

        if event_moderator_crud.get_event_moderator(
            db,
            event_id=event_id,
            user_id=current_user.id,
        ) is not None:
            return

        raise AuthorizationError("You don't have permission to delete this event.")

    raise AuthorizationError("You don't have permission to delete this event.")


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
def create_event(
    payload: EventCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> EventRead:
    _ensure_event_creator(db, payload.group_id, current_user)
    return event_crud.create_event(
        db,
        group_id=payload.group_id,
        title=payload.title,
        description=payload.description,
        cover_image_url=payload.cover_image_url,
        location=payload.location,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )


@router.get("", response_model=list[EventListResponse])
def list_events(
    db: DBSession,
    current_user: OptionalCurrentUser,
    group_id: UUID | None = Query(default=None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> list[EventListResponse]:
    events = event_crud.list_events(db, group_id=group_id, skip=skip, limit=limit)
    return [
        EventListResponse(
            id=event.id,
            title=event.title,
            description=event.description,
            cover_image_url=event.cover_image_url,
            starts_at=event.start_time,
            ends_at=event.end_time,
            location=event.location,
            attendee_count=event_crud.count_event_participants(db, event_id=event.id),
            is_joined=(
                current_user is not None
                and event_crud.get_event_participant(
                    db,
                    event_id=event.id,
                    user_id=current_user.id,
                )
                is not None
            ),
        )
        for event in events
    ]


@router.get("/{event_id}", response_model=EventDetailResponse)
def get_event(
    event_id: UUID,
    db: DBSession,
    current_user: OptionalCurrentUser,
) -> EventDetailResponse:
    event = event_crud.get_event(db, event_id)
    participants = event_crud.list_event_participants(db, event_id=event.id)
    attendee_count = len(participants)
    return EventDetailResponse(
        id=event.id,
        title=event.title,
        description=event.description,
        cover_image_url=event.cover_image_url,
        starts_at=event.start_time,
        ends_at=event.end_time,
        location=event.location,
        attendee_count=attendee_count,
        is_joined=(
            current_user is not None
            and event_crud.get_event_participant(
                db,
                event_id=event.id,
                user_id=current_user.id,
            )
            is not None
        ),
        related_group=(
            EventRelatedGroupResponse(id=event.group.id, name=event.group.name)
            if event.group is not None
            else None
        ),
        participants_preview=[
            EventParticipantPreviewResponse(
                id=participant.id,
                name=participant.full_name,
                avatar_url=participant.avatar_url,
            )
            for participant in participants[:5]
        ],
    )


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
    _ensure_event_deleter(db, event_id, current_user)
    event_crud.delete_event(db, db_obj=event)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{event_id}/join", response_model=EventJoinLeaveResponse)
def join_event(
    event_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> EventJoinLeaveResponse:
    event_crud.get_event(db, event_id)
    event_crud.ensure_event_participant(db, event_id=event_id, user_id=current_user.id)
    return EventJoinLeaveResponse(success=True)


@router.post("/{event_id}/leave", response_model=EventJoinLeaveResponse)
def leave_event(
    event_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> EventJoinLeaveResponse:
    event_crud.get_event(db, event_id)
    event_crud.remove_event_participant(db, event_id=event_id, user_id=current_user.id)
    return EventJoinLeaveResponse(success=True)


@router.get("/{event_id}/participants", response_model=list[EventParticipantResponse])
def list_event_participants(
    event_id: UUID,
    db: DBSession,
    current_user: OptionalCurrentUser,
) -> list[EventParticipantResponse]:
    event_crud.get_event(db, event_id)
    return [
        EventParticipantResponse(
            id=participant.id,
            name=participant.full_name,
            avatar_url=participant.avatar_url,
        )
        for participant in event_crud.list_event_participants(db, event_id=event_id)
    ]


@router.post("/{event_id}/moderators/{user_id}", response_model=EventJoinLeaveResponse)
def assign_event_moderator(
    event_id: UUID,
    user_id: UUID,
    db: DBSession,
    current_user: CurrentAdmin,
) -> EventJoinLeaveResponse:
    event_crud.get_event(db, event_id)
    user_crud.get_user(db, user_id)
    event_moderator_crud.ensure_event_moderator(
        db,
        event_id=event_id,
        user_id=user_id,
        assigned_by=current_user.id,
    )
    return EventJoinLeaveResponse(success=True)


@router.delete("/{event_id}/moderators/{user_id}", response_model=EventJoinLeaveResponse)
def remove_event_moderator(
    event_id: UUID,
    user_id: UUID,
    db: DBSession,
    current_user: CurrentAdmin,
) -> EventJoinLeaveResponse:
    event_crud.get_event(db, event_id)
    user_crud.get_user(db, user_id)
    event_moderator_crud.remove_event_moderator(
        db,
        event_id=event_id,
        user_id=user_id,
    )
    return EventJoinLeaveResponse(success=True)
