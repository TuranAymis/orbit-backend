from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CurrentAdmin, CurrentUser, DBSession
from app.core.exceptions import AuthorizationError
from app.crud import event as event_crud
from app.crud import group as group_crud
from app.crud import group_moderator as group_moderator_crud
from app.crud import membership as membership_crud
from app.crud import user as user_crud
from app.schemas.group import GroupCreate, GroupRead, GroupUpdate
from app.schemas.group import (
    GroupDetailResponse,
    GroupEventPreviewResponse,
    GroupFounderResponse,
    GroupJoinResponse,
    GroupListResponse,
    GroupMemberPreviewResponse,
    GroupMemberResponse,
    GroupStatsResponse,
)
from app.utils.enums import MembershipRole, MembershipStatus
from datetime import UTC, datetime


router = APIRouter(prefix="/groups", tags=["Groups"])


@router.post("", response_model=GroupRead, status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupCreate,
    db: DBSession,
    current_user: CurrentAdmin,
) -> GroupRead:
    return group_crud.create_group(
        db,
        name=payload.name,
        description=payload.description,
        cover_image_url=payload.cover_image_url,
        category=payload.category,
        location=payload.location,
        owner_id=current_user.id,
    )


@router.get("", response_model=list[GroupListResponse])
def list_groups(
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> list[GroupListResponse]:
    groups = group_crud.list_groups(db, skip=skip, limit=limit)
    return [
        GroupListResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            member_count=membership_crud.count_memberships_by_group(db, group_id=group.id),
            image_url=group.cover_image_url,
        )
        for group in groups
    ]


@router.get("/{group_id}", response_model=GroupDetailResponse)
def get_group(group_id: UUID, db: DBSession, current_user: CurrentUser) -> GroupDetailResponse:
    group = group_crud.get_group(db, group_id)
    members = membership_crud.list_group_users(db, group_id=group.id)
    member_count = len(members)
    membership = membership_crud.get_membership_by_user_group(
        db,
        user_id=current_user.id,
        group_id=group.id,
    )
    upcoming_events = event_crud.list_upcoming_events_by_group(
        db,
        group_id=group.id,
        from_time=datetime.now(UTC),
    )
    return GroupDetailResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        cover_image_url=group.cover_image_url,
        member_count=member_count,
        is_joined=membership is not None,
        category=group.category,
        location=group.location,
        founder=GroupFounderResponse(id=group.owner.id, name=group.owner.full_name),
        stats=GroupStatsResponse(posts=0, events=len(group.events), members=member_count),
        upcoming_events=[
            GroupEventPreviewResponse(
                id=event.id,
                title=event.title,
                starts_at=event.start_time,
            )
            for event in upcoming_events
        ],
        gallery_preview=[],
        member_preview=[
            GroupMemberPreviewResponse(
                id=member.id,
                name=member.full_name,
                avatar_url=member.avatar_url,
            )
            for member in members[:5]
        ],
    )


@router.put("/{group_id}", response_model=GroupRead)
def update_group(
    group_id: UUID,
    payload: GroupUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> GroupRead:
    group = group_crud.get_group(db, group_id)
    if group.owner_id != current_user.id:
        raise AuthorizationError("Only the group owner can update this group.")

    return group_crud.update_group(
        db,
        db_obj=group,
        update_data=payload.model_dump(exclude_unset=True),
    )


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> Response:
    group = group_crud.get_group(db, group_id)
    if group.owner_id != current_user.id:
        raise AuthorizationError("Only the group owner can delete this group.")

    group_crud.delete_group(db, db_obj=group)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{group_id}/members", response_model=GroupJoinResponse)
def join_group(
    group_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> GroupJoinResponse:
    group_crud.get_group(db, group_id)
    membership_crud.ensure_group_membership(
        db,
        user_id=current_user.id,
        group_id=group_id,
        role=MembershipRole.MEMBER,
        status=MembershipStatus.ACTIVE,
    )
    return GroupJoinResponse(success=True)


@router.get("/{group_id}/members", response_model=list[GroupMemberResponse])
def list_group_members(
    group_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> list[GroupMemberResponse]:
    group_crud.get_group(db, group_id)
    return [
        GroupMemberResponse(
            id=user.id,
            name=user.full_name,
            avatar_url=user.avatar_url,
        )
        for user in membership_crud.list_group_users(db, group_id=group_id)
    ]


@router.post("/{group_id}/moderators/{user_id}", response_model=GroupJoinResponse)
def assign_group_moderator(
    group_id: UUID,
    user_id: UUID,
    db: DBSession,
    current_user: CurrentAdmin,
) -> GroupJoinResponse:
    group_crud.get_group(db, group_id)
    user_crud.get_user(db, user_id)
    group_moderator_crud.ensure_group_moderator(
        db,
        group_id=group_id,
        user_id=user_id,
        assigned_by=current_user.id,
    )
    return GroupJoinResponse(success=True)


@router.delete("/{group_id}/moderators/{user_id}", response_model=GroupJoinResponse)
def remove_group_moderator(
    group_id: UUID,
    user_id: UUID,
    db: DBSession,
    current_user: CurrentAdmin,
) -> GroupJoinResponse:
    group_crud.get_group(db, group_id)
    user_crud.get_user(db, user_id)
    group_moderator_crud.remove_group_moderator(
        db,
        group_id=group_id,
        user_id=user_id,
    )
    return GroupJoinResponse(success=True)
