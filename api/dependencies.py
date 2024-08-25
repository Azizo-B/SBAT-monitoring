from functools import lru_cache
from typing import AsyncGenerator, Callable, Coroutine

import jwt
from aiocache import cached
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .db.base_repo import BaseRepository
from .db.mongo_repo import MongoRepository
from .models.sbat import MonitorConfiguration
from .models.settings import Settings
from .models.subscriber import SubscriberRead
from .services.sbat_monitor import SbatMonitor


@lru_cache
def get_settings() -> Settings:
    return Settings()


client: AsyncIOMotorClient = AsyncIOMotorClient(get_settings().database_url)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


async def get_mongodb() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    yield client["rijexamen-meldingen"]


def get_repo(db_type: str) -> Callable[..., Coroutine]:
    if db_type == "mongodb":

        async def _get_mongo_repo(mongo_db: AsyncIOMotorDatabase = Depends(get_mongodb)) -> MongoRepository:
            return MongoRepository(mongo_db)

        return _get_mongo_repo

    # elif db_type == "sql":
    #     async def _get_sqlalchemy_repo(sqlalchemy_db: AsyncSession = Depends(get_sqldb)) -> SQLAlchemyRepository:
    #         return SQLAlchemyRepository(sqlalchemy_db)

    #     return _get_sqlalchemy_repo

    else:
        raise ValueError("Unsupported database type")


@cached()
async def get_sbat_monitor() -> SbatMonitor:
    settings: Settings = get_settings()
    repo = await get_repo("mongodb")(mongo_db=client["rijexamen-meldingen"])
    return SbatMonitor(repo=repo, settings=settings, config=MonitorConfiguration())


async def get_current_user(
    token: str = Depends(oauth2_scheme), repo: BaseRepository = Depends(get_repo("mongodb")), settings: Settings = Depends(get_settings)
) -> SubscriberRead:
    credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})

    try:
        payload: dict = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        email: str = payload.get("sub", "")
    except jwt.InvalidTokenError as ite:
        raise credentials_exception from ite

    subscriber: SubscriberRead | None = await repo.find_subscriber_by_email(email)
    if not subscriber:
        raise credentials_exception

    return subscriber


async def get_admin_user(current_user: SubscriberRead = Depends(get_current_user)) -> SubscriberRead:
    if not current_user.role == "admin":
        raise HTTPException(
            status_code=403,
            detail="Not enough privileges",
        )
    return current_user
