from datetime import datetime

from pydantic import BaseModel


class BadgeResponse(BaseModel):
    key: str
    title: str
    description: str
    earned: bool
    awarded_at: datetime | None
