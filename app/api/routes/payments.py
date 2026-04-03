from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DBSession
from app.crud import payment as payment_crud
from app.schemas.payment import PaymentCreate, PaymentRead


router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> PaymentRead:
    return payment_crud.create_payment(
        db,
        user_id=current_user.id,
        amount=payload.amount,
        currency=payload.currency,
        status=payload.status,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )


@router.get("", response_model=list[PaymentRead])
def list_payments(
    db: DBSession,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> list[PaymentRead]:
    return payment_crud.list_payments_by_user(
        db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )


@router.get("/{payment_id}", response_model=PaymentRead)
def get_payment(
    payment_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> PaymentRead:
    return payment_crud.get_payment_for_user(
        db,
        payment_id=payment_id,
        user_id=current_user.id,
    )
