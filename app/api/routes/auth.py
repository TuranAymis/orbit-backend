from fastapi import APIRouter, Request, status

from app.api.deps import DBSession
from app.schemas.auth import (
    AuthActionResponse,
    LoginRequest,
    RegisterRequest,
    ResendVerificationCodeRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.services import auth_service


router = APIRouter(prefix="/auth", tags=["Auth"])


def _request_meta(request: Request) -> tuple[str | None, str | None]:
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return ip_address, user_agent


@router.post("/register", response_model=AuthActionResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: DBSession) -> AuthActionResponse:
    ip_address, user_agent = _request_meta(request)
    return auth_service.register_user(
        db,
        payload=payload,
        ip_address=ip_address,
        user_agent=user_agent,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: DBSession) -> TokenResponse:
    ip_address, user_agent = _request_meta(request)
    return auth_service.login_user(
        db,
        payload=payload,
        ip_address=ip_address,
        user_agent=user_agent,
    )


@router.post("/verify-email", response_model=AuthActionResponse)
def verify_email(payload: VerifyEmailRequest, request: Request, db: DBSession) -> AuthActionResponse:
    ip_address, user_agent = _request_meta(request)
    return auth_service.verify_email_code(
        db,
        payload=payload,
        ip_address=ip_address,
        user_agent=user_agent,
    )


@router.post("/resend-verification-code", response_model=AuthActionResponse)
def resend_verification_code(
    payload: ResendVerificationCodeRequest,
    request: Request,
    db: DBSession,
) -> AuthActionResponse:
    ip_address, user_agent = _request_meta(request)
    return auth_service.resend_verification_code(
        db,
        payload=payload,
        ip_address=ip_address,
        user_agent=user_agent,
    )
