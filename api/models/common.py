from datetime import datetime
from typing import Annotated

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, Field

PyObjectId = Annotated[str, BeforeValidator(lambda v: str(ObjectId(v)))]


class ReferenceBase(BaseModel):
    ip: str
    body: dict
    headers: dict
    timestamp: datetime


class ReferenceCreate(ReferenceBase):
    pass


class ReferenceRead(ReferenceBase):
    id: PyObjectId = Field(..., alias="_id")
