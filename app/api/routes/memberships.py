from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DBSession
from app.core.exceptions import AuthorizationError
from app.crud import group as group_crud
from app.crud import membership as membership_crud
from app.crud import user as user_crud
from app.schemas.membership import MembershipCreate, MembershipRead
from app.utils.enums import MembershipRole, MembershipStatus


router = APIRouter(prefix="/groups", tags=["Memberships"])


@router.post(
    "/{group_id}/members",
    response_model=MembershipRead,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def add_group_member(
    group_id: UUID,
    payload: MembershipCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> MembershipRead:
    group = group_crud.get_group(db, group_id)
    is_group_owner = group.owner_id == current_user.id

    target_user_id = payload.user_id or current_user.id
    if target_user_id != current_user.id and not is_group_owner:
        raise AuthorizationError("Only the group owner can add other users to the group.")

    if target_user_id != current_user.id:
        user_crud.get_user(db, target_user_id)

    role = payload.role if is_group_owner else MembershipRole.MEMBER
    status_value = payload.status if is_group_owner else MembershipStatus.PENDING

    return membership_crud.create_membership(
        db,
        user_id=target_user_id,
        group_id=group_id,
        role=role,
        status=status_value,
    )


@router.get("/{group_id}/members", response_model=list[MembershipRead], include_in_schema=False)
def list_group_members(
    group_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> list[MembershipRead]:
    group_crud.get_group(db, group_id)
    return membership_crud.list_memberships_by_group(db, group_id=group_id)
