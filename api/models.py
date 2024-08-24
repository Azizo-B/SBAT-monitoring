from datetime import UTC, datetime
from typing import Annotated, Literal

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, EmailStr, Field, PositiveInt, field_validator

PyObjectId = Annotated[str, BeforeValidator(lambda v: str(ObjectId(v)))]


class MonitorStatus(BaseModel):
    running: bool
    seconds_inbetween: int
    license_types: list[str]
    exam_centers: list[str]
    task_done: bool | None = None
    total_time_running: str
    first_started_at: datetime | None = None
    last_started_at: datetime | None = None
    last_stopped_at: datetime | None = None
    stopped_due_to: str | None = None


EXAM_CENTER_MAP: dict[int, str] = {1: "sintdenijswestrem", 7: "brakel", 8: "eeklo", 9: "erembodegem", 10: "sintniklaas"}


class MonitorPreferences(BaseModel):
    license_types: list[Literal["B", "AM"]] = ["B"]
    exam_center_ids: list[int] = [1]

    @field_validator("exam_center_ids")
    def validate_exam_center_ids(cls, value):  # pylint: disable=no-self-argument
        if not all(id in EXAM_CENTER_MAP for id in value):
            raise ValueError("One or more exam center IDs are invalid.")
        return value


class MonitorConfiguration(MonitorPreferences):
    seconds_inbetween: PositiveInt = 300


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


class SbatRequestBase(BaseModel):
    timestamp: datetime
    request_type: str
    request_body: dict | None = None
    response: dict | None = None
    url: str
    email_used: str


class SbatRequestCreate(SbatRequestBase):
    pass


class SbatRequestRead(SbatRequestBase):
    _id: PyObjectId


class ExamTimeSlotBase(BaseModel):
    exam_id: int

    first_found_at: datetime = datetime.now(UTC)
    first_taken_at: datetime | None = None
    found_at: datetime = datetime.now(UTC)
    taken_at: datetime | None = None

    start_time: datetime
    end_time: datetime
    status: str

    is_public: bool | None = None
    day_id: int | None = None
    driving_school: str | None = None
    exam_center_id: int | None = None
    exam_type: str | None = None
    examinee: str | None = None
    types_blob: list[str]


class ExamTimeSlotCreate(ExamTimeSlotBase):
    pass


class ExamTimeSlotRead(ExamTimeSlotBase):
    _id: PyObjectId
