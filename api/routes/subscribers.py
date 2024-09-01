from typing import Annotated, Optional

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException
from httpx import AsyncClient, Response

from ..db.base_repo import BaseRepository
from ..dependencies import get_current_user, get_repo, get_settings
from ..helpers import assign_roles_based_on_preferences
from ..models.common import BasicApiResponse
from ..models.discord import DiscordSubscriptionRoles
from ..models.settings import Settings
from ..models.subscriber import MonitorPreferences, SubscriberRead
from ..utils import is_user_in_guild, remove_role_from_user

router = APIRouter(prefix="/subscribers", tags=["Subscribers"])


@router.get("/me")
async def read_users_me(current_user: SubscriberRead = Depends(get_current_user)) -> SubscriberRead:
    return current_user


@router.patch("/me/telegram-account")
async def update_telegram_account(
    telegram_user: dict, current_user: SubscriberRead = Depends(get_current_user), repo: BaseRepository = Depends(get_repo("mongodb"))
) -> BasicApiResponse:
    await repo.update_one("subscribers", {"_id": ObjectId(current_user.id)}, {"telegram_user": telegram_user}, SubscriberRead)
    return BasicApiResponse(detail="Telegram account updated!")


@router.patch("/me/discord-account")
async def update_discord_account(
    token: Annotated[Optional[str], Body(description="OAuth2 token to fetch Discord user data if provided.")] = None,
    discord_user: Annotated[Optional[dict], Body(description="Dictionary containing the Discord user data.")] = None,
    current_user: SubscriberRead = Depends(get_current_user),
    repo: BaseRepository = Depends(get_repo("mongodb")),
    settings: Settings = Depends(get_settings),
) -> BasicApiResponse:
    discord_user_id: str = current_user.discord_user.get("id")
    if await is_user_in_guild(settings.discord_guild_id, discord_user_id, settings.discord_bot_token):
        await remove_role_from_user(
            settings.discord_guild_id, discord_user_id, DiscordSubscriptionRoles.ACTIVE.value, settings.discord_bot_token
        )

    if token:
        async with AsyncClient() as client:
            user_response: Response = await client.get(
                "https://discord.com/api/v10/users/@me", headers={"Authorization": f"Bearer {token}"}
            )
        if user_response.status_code != 200:
            raise HTTPException(status_code=user_response.status_code, detail="Failed to get user information")
        discord_user = user_response.json()

    if discord_user is None:
        raise HTTPException(status_code=400, detail="Valid Discord user data is required")

    await repo.update_one("subscribers", {"_id": ObjectId(current_user.id)}, {"discord_user": discord_user}, SubscriberRead)
    return BasicApiResponse(detail="Discord account updated!")


@router.patch("/me/preferences")
async def update_users_monitoring_preferences(
    wants_emails: bool,
    preferences: MonitorPreferences,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    repo: BaseRepository = Depends(get_repo("mongodb")),
    settings: Settings = Depends(get_settings),
) -> BasicApiResponse:
    await repo.update_one(
        "subscribers",
        {"_id": ObjectId(current_user.id)},
        {"wants_emails": wants_emails, "monitoring_preferences": preferences.model_dump()},
        SubscriberRead,
    )

    discord_user_id = current_user.discord_user.get("id")
    if await is_user_in_guild(settings.discord_guild_id, discord_user_id, settings.discord_bot_token):
        background_tasks.add_task(assign_roles_based_on_preferences, preferences, discord_user_id, settings)

    return BasicApiResponse(detail="Preferences updated!")
