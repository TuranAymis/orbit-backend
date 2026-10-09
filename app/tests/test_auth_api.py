from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.email_verification_code import EmailVerificationCode
from app.models.user import User


PASSWORD = "Password123!"


def _register(client, email: str = "new@example.com"):
    return client.post(
        "/auth/register",
        json={"full_name": "New User", "email": email, "password": PASSWORD},
    )


def test_register_creates_inactive_user_and_sends_code(
    client, db_session: Session, sent_verification_codes
) -> None:
    response = _register(client)

    assert response.status_code == 201
    assert response.json()["message"] == "Verification code sent to email"
    user = db_session.scalar(select(User).where(User.email == "new@example.com"))
    assert user is not None
    assert user.is_active is False
    assert len(sent_verification_codes) == 1
    assert sent_verification_codes[0][0] == user.email
    assert len(sent_verification_codes[0][1]) == 6


def test_login_is_blocked_until_email_is_verified(client) -> None:
    assert _register(client).status_code == 201

    response = client.post(
        "/auth/login", json={"email": "new@example.com", "password": PASSWORD}
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Email not verified"


def test_wrong_verification_code_fails(client, sent_verification_codes) -> None:
    assert _register(client).status_code == 201
    actual_code = sent_verification_codes[0][1]
    wrong_code = "000000" if actual_code != "000000" else "111111"

    response = client.post(
        "/auth/verify-email", json={"email": "new@example.com", "code": wrong_code}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid verification code."


def test_expired_verification_code_fails(
    client, db_session: Session, sent_verification_codes
) -> None:
    assert _register(client).status_code == 201
    verification_code = db_session.scalar(select(EmailVerificationCode))
    assert verification_code is not None
    verification_code.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.commit()

    response = client.post(
        "/auth/verify-email",
        json={"email": "new@example.com", "code": sent_verification_codes[0][1]},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Verification code expired."


def test_verification_activates_user_and_allows_login(
    client, db_session: Session, sent_verification_codes
) -> None:
    assert _register(client).status_code == 201

    response = client.post(
        "/auth/verify-email",
        json={"email": "new@example.com", "code": sent_verification_codes[0][1]},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Account verified successfully"
    user = db_session.scalar(select(User).where(User.email == "new@example.com"))
    db_session.refresh(user)
    assert user.is_active is True
    login = client.post(
        "/auth/login", json={"email": "new@example.com", "password": PASSWORD}
    )
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
    assert login.json()["access_token"]


def test_resend_cooldown_returns_429(client, sent_verification_codes) -> None:
    assert _register(client).status_code == 201
    payload = {"email": "new@example.com"}
    assert client.post("/auth/resend-verification-code", json=payload).status_code == 200

    response = client.post("/auth/resend-verification-code", json=payload)

    assert response.status_code == 429
    assert response.json()["detail"] == (
        "Please wait before requesting another verification code."
    )
    assert len(sent_verification_codes) == 2


def test_duplicate_email_registration_returns_409(client, sent_verification_codes) -> None:
    assert _register(client).status_code == 201

    response = _register(client)

    assert response.status_code == 409
    assert response.json()["detail"] == "A user with this email already exists."
    assert len(sent_verification_codes) == 1
