from ..db.base_repo import BaseRepository
from ..models.subscriber import SubscriberRead


async def handle_start(repo: BaseRepository, message: dict) -> str:
    try:
        telegram_user: dict = message.get("from", {})
        if message.get("chat", {}).get("type") == "private":
            subscriber: SubscriberRead | None = await repo.find_subscriber_by_telegram_user_id(telegram_user.get("id"))
            if not subscriber:
                return "U zit niet in ons systeem, login en link je telegram account: https://rijexamenmeldingen.be/profile"

            if subscriber.is_subscription_active:
                return (
                    f'Hallo {telegram_user.get("first_name", "gebruiker")},\n'
                    f"uw abonnement is actief en je zit in ons systeem als {subscriber.email}."
                )
            else:
                return (
                    "U zit in ons systeem, maar uw abonnement is niet actief. Activeer deze door https://rijexamenmeldingen.be te bezoeken."
                )
        return (
            f"Hallo {telegram_user.get('first_name', 'gebruiker')}, "
            "stuur een /start bericht naar @SbatMonitoringBot in een privégesprek om privé meldingen te ontvangen."
        )
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error in handle_start: {e}")
        return "Er is een fout opgetreden bij het verwerken van uw verzoek. Probeer het later opnieuw."


async def handle_voorkeuren(message: dict) -> str:
    return (
        f"Hallo {message.get('from', {}).get('first_name', 'gebruiker')},\n"
        "dit lukt momenteel nog niet via onze telegram bot.\n"
        "Bezoek https://rijexamenmeldingen.be/profile om je voorkeuren aan te passen."
    )
