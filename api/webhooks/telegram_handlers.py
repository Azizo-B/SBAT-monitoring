from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from api.db import mongoDB

from ..dependencies import Settings
from ..models import SubscriberRead
from ..utils import accept_join_request, decline_join_request, revoke_invite_link


async def handle_chat_join_request(db: AsyncIOMotorDatabase, settings: Settings, update: dict):
    upt: dict | None = await db["telegram_events"].find_one({"update_id": update.get("update_id")})
    if not upt:
        await db["telegram_events"].insert_one(update)

    chat_join_request: dict = update["chat_join_request"]
    if str(chat_join_request.get("chat", {}).get("id")) == settings.telegram_chat_id:
        invt: str = chat_join_request.get("invite_link").get("invite_link")
        telegram_user: dict = chat_join_request.get("from")

        subscriber: SubscriberRead | None = await mongoDB.get_subscriber(db, {"telegram_link": invt})
        if subscriber and not subscriber.telegram_user:
            await db["subscribers"].update_one({"_id": ObjectId(subscriber.id)}, {"$set": {"telegram_user": telegram_user}})
            await accept_join_request(settings.telegram_chat_id, telegram_user.get("id"), settings.telegram_bot_token)
            await revoke_invite_link(settings.telegram_chat_id, invt, settings.telegram_bot_token)
        else:
            await decline_join_request(settings.telegram_chat_id, telegram_user.get("id"), settings.telegram_bot_token)


async def handle_start(db: AsyncIOMotorDatabase, telegram_user: dict) -> str:
    try:
        subscriber: dict | None = await db["subscribers"].find_one({"telegram_user.id": telegram_user.get("id")})
        if not subscriber:
            return "U zit niet in ons systeem"

        subscriber_o: SubscriberRead = SubscriberRead.model_validate(subscriber)
        if subscriber_o.is_subscription_active:
            return f'Hallo {telegram_user.get("first_name", "gebtuiker")}, uw abonnement is actief en je zit in ons systeem als {subscriber_o.email}.'
        else:
            return "U zit in ons systeem, maar uw abonnement is niet actief. Activeer deze door rijexamenmeldingen.be te bezoeken."
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error in handle_start: {e}")
        return "Er is een fout opgetreden bij het verwerken van uw verzoek. Probeer het later opnieuw."
