from fastapi import APIRouter, Depends

from ..db.base_repo import BaseRepository
from ..dependencies import get_admin_user, get_current_user, get_repo
from ..models.subscriber import MonitorPreferences, SubscriberRead

router = APIRouter(prefix="/subscribers", tags=["Subscribers"])


@router.get("/")
async def get_subscribers(
    limit: int = 10, repo: BaseRepository = Depends(get_repo("mongodb")), _: SubscriberRead = Depends(get_admin_user)
) -> list[SubscriberRead]:
    return await repo.list_subscribers(limit)


@router.get("/me")
async def read_users_me(current_user: SubscriberRead = Depends(get_current_user)) -> SubscriberRead:
    return current_user


@router.post("/me/preferences")
async def update_users_monitoring_preferences(
    preferences: MonitorPreferences, current_user=Depends(get_current_user), repo: BaseRepository = Depends(get_repo("mongodb"))
) -> dict[str, str]:
    await repo.update_subscriber_preferences(current_user.id, preferences)
    return {"detail": "Preferences saved!"}
