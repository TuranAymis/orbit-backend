import argparse
from datetime import UTC, datetime, timedelta

from app.core.exceptions import DuplicateResourceError
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.crud import event as event_crud
from app.crud import group as group_crud
from app.crud import chat as chat_crud
from app.crud import membership as membership_crud
from app.crud import notification as notification_crud
from app.crud import user as user_crud
from app.schemas.auth import RegisterRequest
from app.services.auth_service import register_user
from app.utils.enums import MembershipLevel, MembershipRole, MembershipStatus


DEFAULT_USERS = (
    {
        "full_name": "Paid Orbit User",
        "email": "paid@orbit.local",
        "password": "123456",
        "membership_level": MembershipLevel.PAID,
    },
    {
        "full_name": "Free Orbit User",
        "email": "free@orbit.local",
        "password": "123456",
        "membership_level": MembershipLevel.FREE,
    },
)

DEFAULT_GROUPS = (
    {
        "name": "Orbit Builders",
        "description": "A local-first group for people building Orbit together.",
        "cover_image_url": "https://example.com/groups/orbit-builders.jpg",
        "category": "Technology",
        "location": "Remote",
        "owner_email": "free@orbit.local",
        "members": ["free@orbit.local"],
        "chat_messages": [
            {
                "sender_email": "free@orbit.local",
                "content": "Welcome to Orbit Builders.",
            }
        ],
        "events": [
            {
                "title": "Weekly Build Sync",
                "description": "Ship check-in for local Orbit development.",
                "cover_image_url": "https://example.com/events/build-sync.jpg",
                "location": "Remote",
                "start_offset_days": 3,
                "duration_hours": 2,
                "participants": ["free@orbit.local"],
            }
        ],
    },
    {
        "name": "Orbit Founders Circle",
        "description": "Founders and operators sharing growth notes.",
        "cover_image_url": "https://example.com/groups/founders-circle.jpg",
        "category": "Business",
        "location": "Istanbul",
        "owner_email": "paid@orbit.local",
        "members": ["paid@orbit.local"],
        "chat_messages": [
            {
                "sender_email": "paid@orbit.local",
                "content": "Founder sync starts here.",
            }
        ],
        "events": [
            {
                "title": "Founder Office Hours",
                "description": "Weekly founder Q&A and planning session.",
                "cover_image_url": "https://example.com/events/founder-office-hours.jpg",
                "location": "Istanbul",
                "start_offset_days": 5,
                "duration_hours": 1,
                "participants": ["paid@orbit.local"],
            }
        ],
    },
)

DEFAULT_NOTIFICATIONS = (
    {
        "user_email": "paid@orbit.local",
        "type": "group_joined",
        "title": "New member joined",
        "message": "Alex joined Frontend Forge",
        "is_read": False,
        "related_entity_type": "group",
        "related_group_name": "Orbit Founders Circle",
    },
    {
        "user_email": "paid@orbit.local",
        "type": "event_reminder",
        "title": "Upcoming event",
        "message": "Founder Office Hours starts soon",
        "is_read": True,
        "related_entity_type": "event",
        "related_event_title": "Founder Office Hours",
    },
    {
        "user_email": "free@orbit.local",
        "type": "membership",
        "title": "Welcome to Orbit",
        "message": "Your free membership is active",
        "is_read": False,
        "related_entity_type": "membership",
    },
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed local Orbit auth users.")
    parser.add_argument("--full-name", default="Paid Orbit User")
    parser.add_argument("--email", default="paid@orbit.local")
    parser.add_argument("--password", default="123456")
    parser.add_argument(
        "--membership-level",
        default=MembershipLevel.PAID.value,
        choices=[level.value for level in MembershipLevel],
    )
    parser.add_argument(
        "--default-users",
        action="store_true",
        help="Seed the default paid/free users and demo groups idempotently.",
    )
    return parser


def seed_user(db, *, full_name: str, email: str, password: str, membership_level: MembershipLevel) -> None:
    existing_user = user_crud.get_user_by_email(db, email)
    if existing_user is not None:
        existing_user.full_name = full_name.strip()
        existing_user.password_hash = hash_password(password)
        existing_user.membership_level = membership_level
        existing_user.is_active = True
        db.add(existing_user)
        db.commit()
        db.refresh(existing_user)
        print(f"Updated bootstrap user: {existing_user.email} ({existing_user.id})")
        return

    try:
        user = register_user(
            db,
            payload=RegisterRequest(
                full_name=full_name,
                email=email,
                password=password,
                membership_level=membership_level,
            ),
        )
        print(f"Created bootstrap user: {user.email} ({user.id})")
    except DuplicateResourceError:
        print(f"User already exists: {email}")


def seed_default_groups(db) -> None:
    for group_data in DEFAULT_GROUPS:
        existing_group = group_crud.get_group_by_name(db, name=group_data["name"])
        owner = user_crud.get_user_by_email(db, group_data["owner_email"])
        if owner is None:
            continue

        if existing_group is None:
            group = group_crud.create_group(
                db,
                name=group_data["name"],
                description=group_data["description"],
                cover_image_url=group_data["cover_image_url"],
                category=group_data["category"],
                location=group_data["location"],
                owner_id=owner.id,
            )
            print(f"Created demo group: {group.name} ({group.id})")
        else:
            group = group_crud.update_group(
                db,
                db_obj=existing_group,
                update_data={
                    "description": group_data["description"],
                    "cover_image_url": group_data["cover_image_url"],
                    "category": group_data["category"],
                    "location": group_data["location"],
                },
            )
            membership_crud.ensure_group_membership(
                db,
                user_id=owner.id,
                group_id=group.id,
                role=MembershipRole.OWNER,
                status=MembershipStatus.ACTIVE,
            )
            print(f"Updated demo group: {group.name} ({group.id})")

        for member_email in group_data["members"]:
            member = user_crud.get_user_by_email(db, member_email)
            if member is None:
                continue
            role = MembershipRole.OWNER if member.id == owner.id else MembershipRole.MEMBER
            membership_crud.ensure_group_membership(
                db,
                user_id=member.id,
                group_id=group.id,
                role=role,
                status=MembershipStatus.ACTIVE,
            )

        for message_data in group_data.get("chat_messages", []):
            sender = user_crud.get_user_by_email(db, message_data["sender_email"])
            if sender is None:
                continue
            existing_chat = chat_crud.get_chat_by_context_and_message(
                db,
                sender_id=sender.id,
                group_id=group.id,
                event_id=None,
                message=message_data["content"],
            )
            if existing_chat is not None:
                continue
            chat_crud.create_chat(
                db,
                sender_id=sender.id,
                group_id=group.id,
                event_id=None,
                message=message_data["content"],
            )
            print(f"Created demo chat message for {group.name}")

        existing_events = {event.title for event in group.events}
        for event_data in group_data["events"]:
            existing_event = event_crud.get_event_by_title_for_group(
                db,
                group_id=group.id,
                title=event_data["title"],
            )
            if existing_event is None:
                start_time = datetime.now(UTC) + timedelta(days=event_data["start_offset_days"])
                end_time = start_time + timedelta(hours=event_data["duration_hours"])
                event = event_crud.create_event(
                    db,
                    group_id=group.id,
                    title=event_data["title"],
                    description=event_data["description"],
                    cover_image_url=event_data["cover_image_url"],
                    location=event_data["location"],
                    start_time=start_time,
                    end_time=end_time,
                )
                print(f"Created demo event: {event_data['title']} for {group.name}")
            else:
                event = event_crud.update_event(
                    db,
                    db_obj=existing_event,
                    update_data={
                        "description": event_data["description"],
                        "cover_image_url": event_data["cover_image_url"],
                        "location": event_data["location"],
                    },
                )

            for participant_email in event_data.get("participants", []):
                participant = user_crud.get_user_by_email(db, participant_email)
                if participant is None:
                    continue
                event_crud.ensure_event_participant(
                    db,
                    event_id=event.id,
                    user_id=participant.id,
                )


def seed_notifications(db) -> None:
    for notification_data in DEFAULT_NOTIFICATIONS:
        user = user_crud.get_user_by_email(db, notification_data["user_email"])
        if user is None:
            continue

        related_entity_id = None
        if notification_data.get("related_group_name"):
            group = group_crud.get_group_by_name(db, name=notification_data["related_group_name"])
            related_entity_id = group.id if group is not None else None
        if notification_data.get("related_event_title"):
            for group_data in DEFAULT_GROUPS:
                group = group_crud.get_group_by_name(db, name=group_data["name"])
                if group is None:
                    continue
                event = event_crud.get_event_by_title_for_group(
                    db,
                    group_id=group.id,
                    title=notification_data["related_event_title"],
                )
                if event is not None:
                    related_entity_id = event.id
                    break

        existing_notification = notification_crud.get_notification_by_signature(
            db,
            user_id=user.id,
            type=notification_data["type"],
            title=notification_data["title"],
            message=notification_data["message"],
        )
        if existing_notification is not None:
            existing_notification.is_read = notification_data["is_read"]
            existing_notification.related_entity_type = notification_data.get("related_entity_type")
            existing_notification.related_entity_id = related_entity_id
            db.add(existing_notification)
            db.commit()
            continue

        notification_crud.create_notification(
            db,
            user_id=user.id,
            type=notification_data["type"],
            title=notification_data["title"],
            message=notification_data["message"],
            is_read=notification_data["is_read"],
            related_entity_type=notification_data.get("related_entity_type"),
            related_entity_id=related_entity_id,
        )
        print(f"Created demo notification for {user.email}: {notification_data['title']}")


def main() -> None:
    args = build_parser().parse_args()
    db = SessionLocal()

    try:
        if args.default_users:
            for user in DEFAULT_USERS:
                seed_user(db, **user)
            seed_default_groups(db)
            seed_notifications(db)
            return

        seed_user(
            db,
            full_name=args.full_name,
            email=args.email,
            password=args.password,
            membership_level=MembershipLevel(args.membership_level),
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
