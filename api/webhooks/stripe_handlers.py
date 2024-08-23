from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from api.db import mongoDB

from ..dependencies import Settings
from ..models import SubscriberRead
from ..utils import create_single_use_invite_link, send_email


async def handle_invoice_payment_failed(db: AsyncIOMotorDatabase, settings: Settings, invoice: dict) -> None:
    cus: str | None = invoice.get("customer")
    subscriber: SubscriberRead | None = await mongoDB.get_subscriber(db, {"stripe_customer_id": cus})
    if subscriber:
        send_email(
            "Betalingsfout - Actie Vereist",
            [subscriber.email],
            settings.sender_email,
            settings.sender_password,
            settings.smtp_server,
            settings.smtp_port,
            is_html=True,
            html_template="payment_failed_email.html",
            naam=subscriber.name,
        )


async def handle_invoice_payment_succeeded(db: AsyncIOMotorDatabase, invoice: dict) -> None:
    await mongoDB.activate_subscription(db, invoice.get("customer"), invoice.get("amount_paid"))


async def handle_subscription_deleted(db: AsyncIOMotorDatabase, settings: Settings, subscription: dict) -> None:
    cus: str | None = subscription.get("customer")
    await mongoDB.deactivate_subscription(db, cus)
    subscriber: SubscriberRead | None = await mongoDB.get_subscriber(db, {"stripe_customer_id": cus})
    if subscriber:
        send_email(
            "Bevestiging van Annulering van je Abonnement.",
            [subscriber.email],
            settings.sender_email,
            settings.sender_password,
            settings.smtp_server,
            settings.smtp_port,
            is_html=True,
            html_template="cancellation_email.html",
            naam=subscriber.name,
        )


async def handle_checkout_session_completed(db: AsyncIOMotorDatabase, settings: Settings, session: dict) -> None:
    sub: SubscriberRead | None = await mongoDB.get_subscriber(db, {"_id": ObjectId(session.get("client_reference_id"))})
    telegram_link: str | None = await create_single_use_invite_link(
        settings.telegram_chat_id, settings.telegram_bot_token, name=sub.name if sub else None
    )
    subscriber: SubscriberRead = await mongoDB.process_checkout_session(db, session, telegram_link)
    send_email(
        "Betaling geslaagd! Uw voorkeuren zijn ontvangen.",
        [subscriber.email],
        settings.sender_email,
        settings.sender_password,
        settings.smtp_server,
        settings.smtp_port,
        is_html=True,
        html_template="confirmation_email.html",
        naam=subscriber.name,
        telegram_link=telegram_link,
    )
