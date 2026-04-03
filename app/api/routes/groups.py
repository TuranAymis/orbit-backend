from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CurrentUser, DBSession
from app.core.exceptions import AuthorizationError
from app.crud import group as group_crud
from app.schemas.group import GroupCreate, GroupRead, GroupUpdate


router = APIRouter(prefix="/groups", tags=["Groups"])


@router.post("", response_model=GroupRead, status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> GroupRead:
    return group_crud.create_group(
        db,
        name=payload.name,
        description=payload.description,
        owner_id=current_user.id,
    )


@router.get("", response_model=list[GroupRead])
def list_groups(
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> list[GroupRead]:
    return group_crud.list_groups(db, skip=skip, limit=limit)


@router.get("/{group_id}", response_model=GroupRead)
def get_group(group_id: UUID, db: DBSession) -> GroupRead:
    return group_crud.get_group(db, group_id)


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
