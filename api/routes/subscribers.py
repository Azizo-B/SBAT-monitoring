from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from api.db import mongoDB

from ..dependencies import get_admin_user, get_current_user, get_db
from ..models import MonitorPreferences, SubscriberRead

router = APIRouter(prefix="/subscribers", tags=["Subscribers"])


@router.get("/")
async def get_subscribers(db: AsyncIOMotorDatabase = Depends(get_db), _: SubscriberRead = Depends(get_admin_user)) -> list[SubscriberRead]:
    return await mongoDB.get_subscribers(db)


@router.get("/me")
async def read_users_me(current_user: SubscriberRead = Depends(get_current_user)) -> SubscriberRead:
    return current_user


@router.post("/me/preferences")
async def update_users_monitoring_preferences(
    preferences: MonitorPreferences, current_user=Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)
) -> dict[str, str]:
    await mongoDB.update_subscriber_preferences(db, current_user.id, preferences)
    return {"detail": "Preferences saved!"}
