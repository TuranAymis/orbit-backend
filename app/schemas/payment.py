from datetime import date, datetime
from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.utils.enums import PaymentStatus


class PaymentBase(BaseModel):
    amount: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    currency: str = Field(..., min_length=3, max_length=3)
    start_date: date
    end_date: date

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        if self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date.")
        return self


class PaymentCreate(PaymentBase):
    status: PaymentStatus = PaymentStatus.PENDING


class PaymentRead(PaymentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    status: PaymentStatus
    created_at: datetime
