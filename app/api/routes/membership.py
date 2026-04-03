from fastapi import APIRouter

from app.api.deps import CurrentUser, DBSession
from app.schemas.membership import MembershipOverviewResponse, MembershipUpgradeResponse
from app.services import membership_service


router = APIRouter(prefix="/membership", tags=["Membership"])


@router.get("", response_model=MembershipOverviewResponse)
def read_membership(
    db: DBSession,
    current_user: CurrentUser,
) -> MembershipOverviewResponse:
    return membership_service.get_membership_overview(db, user=current_user)


@router.post("/upgrade", response_model=MembershipUpgradeResponse)
def upgrade_membership(
    db: DBSession,
    current_user: CurrentUser,
) -> MembershipUpgradeResponse:
    return membership_service.upgrade_membership(db, user=current_user)
