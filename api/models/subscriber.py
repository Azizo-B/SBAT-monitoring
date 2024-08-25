from datetime import UTC, datetime

from pydantic import BaseModel, EmailStr, Field

from .common import PyObjectId
from .sbat import MonitorPreferences


class SubscriberBase(BaseModel):
    name: str
    email: EmailStr
    stripe_customer_id: str | None = None
    stripe_ids: list[str] = []
    phone: str | None = None
    telegram_link: str | None = None
    telegram_user: dict = {}
    extra_details: dict = {}
    total_spent: int = 0
    role: str = "user"
    is_subscription_active: bool = False
    monitoring_preferences: MonitorPreferences = MonitorPreferences()
    account_created_on: datetime = datetime.now(UTC)


class SubscriberCreate(SubscriberBase):
    password: str


class SubscriberRead(SubscriberBase):
    id: PyObjectId = Field(..., alias="_id")
    hashed_password: str
