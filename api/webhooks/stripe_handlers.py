from bson import ObjectId

from ..db.base_repo import BaseRepository
from ..models.settings import Settings
from ..models.subscriber import SubscriberRead
from ..utils import create_single_use_invite_link, send_email


async def handle_invoice_payment_failed(repo: BaseRepository, settings: Settings, invoice: dict) -> None:
    cus: str | None = invoice.get("customer")
    subscriber: SubscriberRead | None = await repo.find_one("subscribers", {"stripe_customer_id": cus}, SubscriberRead)
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


async def handle_invoice_payment_succeeded(repo: BaseRepository, invoice: dict) -> SubscriberRead | None:
    return await repo.activate_subscriber_subscription(invoice.get("customer"), invoice.get("amount_paid"))


async def handle_subscription_deleted(repo: BaseRepository, settings: Settings, subscription: dict) -> None:
    cus: str | None = subscription.get("customer")
    subscriber: SubscriberRead | None = await repo.update_one(
        "subscribers", {"stripe_customer_id": cus}, {"is_subscription_active": False}, SubscriberRead
    )
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


async def handle_checkout_session_completed(repo: BaseRepository, settings: Settings, session: dict) -> None:
    sub: SubscriberRead | None = await repo.find_one("subscribers", {"_id": ObjectId(session.get("client_reference_id"))}, SubscriberRead)
    telegram_link: str | None = await create_single_use_invite_link(
        settings.telegram_chat_id, settings.telegram_bot_token, name=sub.name if sub else None
    )
    subscriber: SubscriberRead = await repo.process_checkout_session(session, telegram_link)
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
