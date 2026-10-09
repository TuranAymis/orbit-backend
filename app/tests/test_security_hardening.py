import pytest
from fastapi import FastAPI, WebSocket

from app.core.config import Settings, settings, validate_production_settings
from app.main import SecurityHeadersMiddleware


SAFE_PRODUCTION_SETTINGS = {
    "ENVIRONMENT": "production",
    "JWT_SECRET_KEY": "a" * 32,
    "DEBUG": False,
    "BACKEND_CORS_ORIGINS": ["https://orbit.example"],
    "EMAIL_SENDER_MODE": "smtp",
}


@pytest.mark.parametrize(
    ("override", "setting"),
    [
        ({"JWT_SECRET_KEY": "change-this-in-production"}, "JWT_SECRET_KEY"),
        ({"JWT_SECRET_KEY": "short"}, "JWT_SECRET_KEY"),
        ({"DEBUG": True}, "DEBUG"),
        ({"BACKEND_CORS_ORIGINS": []}, "BACKEND_CORS_ORIGINS"),
        ({"BACKEND_CORS_ORIGINS": ["*"]}, "BACKEND_CORS_ORIGINS"),
        ({"BACKEND_CORS_ORIGINS": ["http://localhost:3000"]}, "BACKEND_CORS_ORIGINS"),
        ({"BACKEND_CORS_ORIGINS": ["http://127.0.0.1:3000"]}, "BACKEND_CORS_ORIGINS"),
        ({"EMAIL_SENDER_MODE": "console"}, "EMAIL_SENDER_MODE"),
    ],
)
def test_production_rejects_unsafe_settings(override, setting) -> None:
    config = Settings(_env_file=None, **(SAFE_PRODUCTION_SETTINGS | override))

    with pytest.raises(RuntimeError, match=setting):
        validate_production_settings(config)


def test_production_accepts_safe_settings() -> None:
    validate_production_settings(Settings(_env_file=None, **SAFE_PRODUCTION_SETTINGS))


def test_development_keeps_existing_defaults() -> None:
    validate_production_settings(Settings(_env_file=None))


def test_security_headers_on_health(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"


def test_development_has_no_hsts_and_websockets_pass_through() -> None:
    pytest.importorskip("httpx", reason="FastAPI TestClient requires httpx")
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware, production=False)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.websocket("/ws/chat")
    async def chat(websocket: WebSocket) -> None:
        await websocket.accept()
        await websocket.send_text("connected")
        await websocket.close()

    with TestClient(app) as test_client:
        assert "strict-transport-security" not in test_client.get("/health").headers
        with test_client.websocket_connect("/ws/chat") as websocket:
            assert websocket.receive_text() == "connected"


def test_login_rate_limit_counts_unknown_email_failures(client) -> None:
    payload = {"email": "unknown@example.com", "password": "WrongPassword123!"}

    for _ in range(settings.AUTH_LOGIN_RATE_LIMIT_MAX_ATTEMPTS):
        response = client.post("/auth/login", json=payload)
        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect email or password."

    response = client.post("/auth/login", json=payload)
    assert response.status_code == 429
    assert response.json()["detail"] == "Too many login attempts. Please try again later."


def test_successful_login_below_limit(client, make_user) -> None:
    make_user("known@example.com")
    wrong = client.post(
        "/auth/login",
        json={"email": "known@example.com", "password": "WrongPassword123!"},
    )
    assert wrong.status_code == 401
    assert wrong.json()["detail"] == "Incorrect email or password."

    correct = client.post(
        "/auth/login",
        json={"email": "known@example.com", "password": "Password123!"},
    )
    assert correct.status_code == 200
    assert correct.json()["access_token"]


def test_failed_logins_from_another_address_do_not_lock_out_the_real_user(
    client, make_user,
) -> None:
    from app.core.config import settings
    from app.core.exceptions import AuthenticationError, RateLimitError
    from app.services import auth_service
    from app.core.database import SessionLocal  # noqa: F401 - ensures models are loaded

    user = make_user("lockout-victim@example.com", password="Password123!")
    # Same helper the route uses, called with explicit client addresses.
    import app.api.deps as deps

    db = next(client.app.dependency_overrides[deps.get_db]())
    try:
        for _ in range(settings.AUTH_LOGIN_RATE_LIMIT_MAX_ATTEMPTS):
            try:
                auth_service.authenticate_user(
                    db, email=user.email, password="wrong-password", ip_address="203.0.113.7"
                )
            except AuthenticationError:
                pass
        with pytest.raises(RateLimitError):
            auth_service.authenticate_user(
                db, email=user.email, password="Password123!", ip_address="203.0.113.7"
            )
        # The legitimate user, from a different address, can still log in.
        assert auth_service.authenticate_user(
            db, email=user.email, password="Password123!", ip_address="198.51.100.9"
        ).id == user.id
    finally:
        db.close()
