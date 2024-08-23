from functools import lru_cache
from typing import AsyncGenerator

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pydantic_settings import BaseSettings

from .models import SubscriberRead


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

    jwt_secret_key: str
    access_token_expire_minutes: int = 1440
    jwt_algorithm: str = "HS256"

    class Config:
        env_file: str = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()


client: AsyncIOMotorClient = AsyncIOMotorClient(get_settings().database_url)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


async def get_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    yield client["rijexamen-meldingen"]


@lru_cache
def get_sbat_monitor():
    settings: Settings = get_settings()
    db: AsyncIOMotorDatabase = client["rijexamen-meldingen"]

    from .models import MonitorConfiguration  # pylint: disable=import-outside-toplevel
    from .services.sbat_monitor import SbatMonitor  # pylint: disable=import-outside-toplevel

    return SbatMonitor(db=db, settings=settings, config=MonitorConfiguration())


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncIOMotorDatabase = Depends(get_db), settings: Settings = Depends(get_settings)
) -> SubscriberRead:
    credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})

    try:
        payload: dict = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        email: str = payload.get("sub", "")
    except jwt.InvalidTokenError as ite:
        raise credentials_exception from ite

    subscriber: dict | None = await db["subscribers"].find_one({"email": email})
    if not subscriber:
        raise credentials_exception

    return SubscriberRead(**subscriber)


async def get_admin_user(current_user: SubscriberRead = Depends(get_current_user)) -> SubscriberRead:
    if not current_user.role == "admin":
        raise HTTPException(
            status_code=403,
            detail="Not enough privileges",
        )
    return current_user
