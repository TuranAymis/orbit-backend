import os
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_db
from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.crud import user as user_crud
from app.main import app
from app.models.user import User
from app.services import email_service
from app.utils.enums import MembershipLevel, UserRole


@pytest.fixture(scope="session")
def test_engine() -> Iterator[Engine]:
    database_url = os.getenv("ORBIT_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("ORBIT_TEST_DATABASE_URL is required for API integration tests")

    # The fixtures TRUNCATE every table, so only ever run against a dedicated test database.
    database_name = make_url(database_url).database or ""
    if "test" not in database_name.lower():
        pytest.exit(
            "ORBIT_TEST_DATABASE_URL must point to a database whose name contains 'test'; "
            "its tables are truncated between tests.",
            returncode=2,
        )

    engine = create_engine(database_url, pool_pre_ping=True)
    # alembic/env.py reads settings.DATABASE_URL when it starts.
    original_url = settings.DATABASE_URL
    try:
        settings.DATABASE_URL = database_url
        config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        command.upgrade(config, "head")
    finally:
        settings.DATABASE_URL = original_url

    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(test_engine: Engine) -> Iterator[Session]:
    with test_engine.begin() as connection:
        tables = [
            table for table in inspect(connection).get_table_names()
            if table != "alembic_version"
        ]
        if tables:
            preparer = test_engine.dialect.identifier_preparer
            names = ", ".join(preparer.quote(table) for table in tables)
            connection.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))

    session_factory = sessionmaker(bind=test_engine, expire_on_commit=False)
    with session_factory() as session:
        yield session


@pytest.fixture
def sent_verification_codes(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    sent: list[tuple[str, str]] = []

    def capture_email(*, email: str, code: str) -> None:
        sent.append((email, code))

    monkeypatch.setattr(email_service, "send_verification_code_email", capture_email)
    return sent


@pytest.fixture
def client(db_session: Session, sent_verification_codes, monkeypatch: pytest.MonkeyPatch):
    pytest.importorskip("httpx", reason="FastAPI TestClient requires httpx")
    from fastapi.testclient import TestClient

    session_factory = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)

    def test_get_db() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = test_get_db
    monkeypatch.setattr("app.services.push_dispatcher.dispatch_in_background", lambda *args: None)
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def make_user(db_session: Session) -> Callable[..., User]:
    def create(
        email: str,
        password: str = "Password123!",
        role: UserRole = UserRole.USER,
        membership_level: MembershipLevel = MembershipLevel.FREE,
        is_active: bool = True,
    ) -> User:
        return user_crud.create_user(
            db_session,
            full_name="API Test User",
            email=email,
            password_hash=hash_password(password),
            role=role,
            membership_level=membership_level,
            is_active=is_active,
        )

    return create


@pytest.fixture
def auth_headers() -> Callable[[User], dict[str, str]]:
    def headers(user: User) -> dict[str, str]:
        return {"Authorization": f"Bearer {create_access_token(subject=str(user.id))}"}

    return headers
