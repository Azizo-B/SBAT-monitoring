from enum import Enum

from pydantic import BaseModel, ConfigDict


class DiscordSubscriptionRoles(str, Enum):
    ACTIVE = "1279432303055081624"
    INACTIVE = "1279432629363671071"
    NOT_FOUND = "1279432838168449045"


class DiscordInteraction(BaseModel):
    id: str
    type: int
    data: dict
    model_config = ConfigDict(extra="allow")


class DiscordUser(BaseModel):
    id: str
    model_config = ConfigDict(extra="allow")
