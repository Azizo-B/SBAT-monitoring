import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, EmailStr, Field

from .common import PyObjectId
from .sbat import MonitorPreferences


class SubscriberBase(BaseModel):
    account_created_on: datetime = Field(default_factory=lambda: datetime.now(UTC))
    stripe_customer_id: str | None = None
    name: str
    email: EmailStr
    phone: str | None = None
    role: str = "user"
    total_spent: int = 0
    wants_emails: bool = False
    is_subscription_active: bool = False
    telegram_user: dict = Field(default_factory=dict)
    discord_user: dict = Field(default_factory=dict)
    stripe_ids: list[str] = Field(default_factory=list)
    extra_details: dict = Field(default_factory=dict)
    monitoring_preferences: MonitorPreferences = MonitorPreferences()
    is_verified: bool = False
    verification_token: str = Field(default_factory=lambda: str(uuid.uuid4()))


class SubscriberCreate(SubscriberBase):
    password: str


class SubscriberRead(SubscriberBase):
    id: PyObjectId = Field(..., alias="_id")
    hashed_password: str
