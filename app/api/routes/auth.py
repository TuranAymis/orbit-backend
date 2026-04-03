from fastapi import APIRouter, status

from app.api.deps import DBSession
from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.token import Token
from app.schemas.user import UserRead
from app.services import auth_service


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DBSession) -> UserRead:
    return auth_service.register_user(db, payload=payload)


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: DBSession) -> Token:
    return auth_service.login_user(db, payload=payload)
