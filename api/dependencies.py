from functools import lru_cache
from typing import AsyncGenerator

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str

    sbat_username: str
    sbat_password: str

    stripe_secret_key: str
    stripe_publishable_key: str
    stripe_endpoint_secret: str

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    sender_email: str | None = None
    sender_password: str | None = None
    smtp_server: str | None = None
    smtp_port: int | None = None

    class Config:
        env_file: str = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()


client: AsyncIOMotorClient = AsyncIOMotorClient(get_settings().database_url)


async def get_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    yield client["rijexamen-meldingen"]


@lru_cache
def get_sbat_monitor():
    settings: Settings = get_settings()
    db: AsyncIOMotorDatabase = client["rijexamen-meldingen"]

    from .models import MonitorConfiguration  # pylint: disable=import-outside-toplevel
    from .sbat_monitor import SbatMonitor  # pylint: disable=import-outside-toplevel

    return SbatMonitor(db=db, settings=settings, config=MonitorConfiguration())
