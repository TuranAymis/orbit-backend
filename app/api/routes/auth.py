from fastapi import APIRouter, status

from app.api.deps import DBSession
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserRead
from app.services import auth_service


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DBSession) -> UserRead:
    return auth_service.register_user(db, payload=payload)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DBSession) -> TokenResponse:
    return auth_service.login_user(db, payload=payload)
