from enum import Enum


class MembershipLevel(str, Enum):
    FREE = "free"
    PAID = "paid"


class UserRole(str, Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class MembershipRole(str, Enum):
    MEMBER = "member"
    ADMIN = "admin"
    OWNER = "owner"


class MembershipStatus(str, Enum):
    ACTIVE = "active"
    PENDING = "pending"
    BANNED = "banned"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
