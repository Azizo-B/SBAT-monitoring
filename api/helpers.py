import asyncio

from .models.discord import DiscordSubscriptionRoles
from .models.sbat import EXAM_CENTER_MAP, MonitorPreferences
from .models.settings import Settings
from .utils import assign_role_to_user, get_role_id_by_name, get_user_roles_in_guild, remove_role_from_user


async def assign_roles_based_on_preferences(
    preferences: MonitorPreferences,
    discord_user_id: int,
    settings: Settings,
):
    current_roles = set(await get_user_roles_in_guild(settings.discord_guild_id, discord_user_id, settings.discord_bot_token))

    desired_roles = set()
    for exam_center_id in preferences.exam_center_ids:
        for license_type in preferences.license_types:
            role_id: str = await get_role_id_by_name(
                settings.discord_bot_token, settings.discord_guild_id, f"{EXAM_CENTER_MAP[exam_center_id]} - {license_type}"
            )
            desired_roles.add(role_id)

    subscription_role_ids = set([role.value for role in DiscordSubscriptionRoles])

    active_status_role_id: set = current_roles & subscription_role_ids
    if active_status_role_id:
        desired_roles.add(active_status_role_id.pop())

    roles_to_add: set = desired_roles - current_roles
    roles_to_remove: set = current_roles - desired_roles

    # Avoid discord issues when calling to fast
    for role_id in roles_to_add:
        await assign_role_to_user(settings.discord_guild_id, discord_user_id, role_id, settings.discord_bot_token)
        await asyncio.sleep(2)  # Wait for 2 seconds before the next role assignment

    for role_id in roles_to_remove:
        await remove_role_from_user(settings.discord_guild_id, discord_user_id, role_id, settings.discord_bot_token)
        await asyncio.sleep(2)  # Wait for 2 seconds before the next role removal
