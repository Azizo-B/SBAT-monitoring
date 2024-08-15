from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr
from sqlalchemy import Boolean, Column, DateTime, Integer, String

from .dependencies import Base


class Subscriber(Base):
    __tablename__: str = "subscribers"
    email = Column(String, primary_key=True, index=True)


class SbatRequests(Base):
    __tablename__: str = "sbat_requests"

    id = Column(Integer, primary_key=True, index=True)
    email_used = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.now)
    request_type = Column(String, nullable=False)
    request_body = Column(String, nullable=True)
    response = Column(String, nullable=True)
    response_body = Column(String, nullable=True)
    url = Column(String, nullable=False)


class ExamDate(Base):
    __tablename__: str = "exam_dates"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, unique=True, index=True)

    first_found_at = Column(DateTime, nullable=False, default=datetime.now)
    first_taken_at = Column(DateTime, nullable=True)
    found_at = Column(DateTime, nullable=False, default=datetime.now)
    taken_at = Column(DateTime, nullable=True)

    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(String, nullable=False)

    is_public = Column(Boolean, nullable=True)
    day_id = Column(Integer, nullable=True)
    driving_school = Column(String, nullable=True)
    exam_center_id = Column(Integer, nullable=True)
    exam_type = Column(String, nullable=True)
    examinee = Column(String, nullable=True)
    types_blob = Column(String, nullable=True)


class MonitorConfiguration(BaseModel):
    seconds_inbetween: int | None = None
    license_types: list[Literal["B", "AM"]] | None = None


class MonitorStatus(BaseModel):
    running: bool
    seconds_inbetween: int
    license_types: list[str]
    task_done: bool | None = None
    total_time_running: str
    first_started_at: datetime | None = None
    last_started_at: datetime | None = None
    last_stopped_at: datetime | None = None
    task_exception: str | None = None


class SubscriptionRequest(BaseModel):
    email: EmailStr


class SbatRequestBaseSchema(BaseModel):
    timestamp: datetime
    request_type: str
    request_body: str | None
    response: str | None
    url: str

    class Config:
        from_attributes = True


class SbatRequestCreateSchema(SbatRequestBaseSchema):
    email_used: str


class SbatRequestReadSchema(SbatRequestBaseSchema):
    id: int


class ExamDateSchema(BaseModel):
    id: int
    exam_id: int

    first_found_at: datetime
    first_taken_at: datetime | None = None
    found_at: datetime
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
    types_blob: str | None = None

    class Config:
        from_attributes = True
