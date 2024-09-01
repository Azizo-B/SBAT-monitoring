import asyncio

from fastapi import BackgroundTasks

from api.models.subscriber import SubscriberRead

from ..db.base_repo import BaseRepository
from ..helpers import assign_roles_based_on_preferences
from ..models.discord import DiscordSubscriptionRoles
from ..models.settings import Settings
from ..utils import assign_role_to_user, is_user_in_guild, remove_role_from_user


async def handle_start(background_tasks: BackgroundTasks, repo: BaseRepository, settings: Settings, interaction: dict) -> str:
    discord_user_id: int = interaction.get("member", {}).get("user", {}).get("id") or interaction.get("user", {}).get("id")
    if not await is_user_in_guild(settings.discord_guild_id, discord_user_id, settings.discord_bot_token):
        return (
            "🚫 Het lijkt erop dat je nog geen lid bent van onze server.\n\n"
            "👉 [Klik hier om lid te worden van de server](https://discord.gg/fhA5c4tTww).\n\n"
            "Probeer het opnieuw zodra je lid bent geworden."
        )

    subscriber: SubscriberRead | None = await repo.find_subscriber_by_discord_user_id(discord_user_id)
    for role_id in [role.value for role in DiscordSubscriptionRoles]:
        await remove_role_from_user(settings.discord_guild_id, discord_user_id, role_id, settings.discord_bot_token)
        asyncio.sleep(1)

    if subscriber:
        if subscriber.is_subscription_active:
            await assign_role_to_user(
                settings.discord_guild_id, discord_user_id, DiscordSubscriptionRoles.ACTIVE.value, settings.discord_bot_token
            )
            background_tasks.add_task(assign_roles_based_on_preferences, subscriber.monitoring_preferences, discord_user_id, settings)
            return (
                "🎉 Gefeliciteerd! Je hebt nu de rol **'Subscription Active'** en alle rollen in jouw"
                "[voorkeuren](https://rijexamenmeldingen.be/profile) toegewezen gekregen. "
                "Je hebt volledige toegang tot alle functies en notificaties van onze service.\n\n"
                "🔍 **Wat nu?**\n"
                "Je kunt nu in de relevante kanalen updates ontvangen en vragen stellen."
                "Als je problemen ondervindt of vragen hebt, aarzel dan niet om hulp te vragen in de supportkanalen."
            )
        else:
            await assign_role_to_user(
                settings.discord_guild_id, discord_user_id, DiscordSubscriptionRoles.INACTIVE.value, settings.discord_bot_token
            )
            return (
                "⚠️ Je abonnement is verlopen. Je hebt nu de rol **'Subscription Expired'** toegewezen gekregen.\n\n"
                "🔄 **Wat nu?**\n"
                "Om opnieuw toegang te krijgen tot alle functies, vernieuw je abonnement via onze website https://rijexamenmeldingen.be. "
                "Als je denkt dat dit een fout is, neem dan contact met ons op via de supportkanalen."
            )
    else:
        await assign_role_to_user(
            settings.discord_guild_id, discord_user_id, DiscordSubscriptionRoles.NOT_FOUND.value, settings.discord_bot_token
        )
        return (
            "👋 Welkom! Je hebt nu de rol **'Unsubscribed'** toegewezen gekregen.\n\n"
            "🔍 **Wat nu?**\n"
            "Het lijkt erop dat je nog geen actief abonnement hebt."
            "Bezoek onze https://rijexamenmeldingen.be om je te abonneren en toegang te krijgen tot onze volledige service. "
            "Zodra je bent geabonneerd, kom terug en gebruik het **/start**-commando opnieuw om je rol te activeren."
        )


async def handle_voorkeuren() -> str:
    return "dit lukt momenteel nog niet via onze bot.\n" "Bezoek https://rijexamenmeldingen.be/profile om je voorkeuren aan te passen."
