from pydantic import BaseModel, EmailStr
from sqlalchemy import Boolean, Column, DateTime, Integer, String

from .dependencies import Base


class Subscriber(Base):
    __tablename__: str = "subscribers"
    email = Column(String, primary_key=True, index=True)


class SubscriptionRequest(BaseModel):
    email: EmailStr


class ExamDate(Base):
    __tablename__: str = "exam_dates"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, unique=True, index=True)

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
