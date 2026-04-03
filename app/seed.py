import argparse

from app.core.exceptions import DuplicateResourceError
from app.core.database import SessionLocal
from app.schemas.auth import RegisterRequest
from app.services.auth_service import register_user
from app.utils.enums import MembershipLevel


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed a bootstrap Orbit user.")
    parser.add_argument("--full-name", default="Orbit Admin")
    parser.add_argument("--email", default="admin@example.com")
    parser.add_argument("--password", default="ChangeMe123!")
    parser.add_argument(
        "--membership-level",
        default=MembershipLevel.PAID.value,
        choices=[level.value for level in MembershipLevel],
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    db = SessionLocal()

    try:
        user = register_user(
            db,
            payload=RegisterRequest(
                full_name=args.full_name,
                email=args.email,
                password=args.password,
                membership_level=MembershipLevel(args.membership_level),
            ),
        )
        print(f"Created bootstrap user: {user.email} ({user.id})")
    except DuplicateResourceError:
        print(f"User already exists: {args.email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
