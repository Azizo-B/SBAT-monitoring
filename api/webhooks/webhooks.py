import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..dependencies import Settings, get_db, get_settings
from ..utils import send_telegram_message
from .stripe_handlers import (
    handle_checkout_session_completed,
    handle_invoice_payment_failed,
    handle_invoice_payment_succeeded,
    handle_subscription_deleted,
)
from .telegram_handlers import handle_chat_join_request, handle_start

webhooks = APIRouter(tags=["Webhooks"])


@webhooks.post("/stripe-webhook")
async def stripe_webhook(
    request: Request, settings: Settings = Depends(get_settings), db: AsyncIOMotorDatabase = Depends(get_db)
) -> dict[str, str]:
    stripe.api_key = settings.stripe_secret_key

    payload: bytes = await request.body()
    sig_header: str | None = request.headers.get("stripe-signature")

    try:
        event: stripe.Event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe_endpoint_secret)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload") from e
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature") from e

    evt: dict | None = await db["stripe_events"].find_one({"id": event["id"]})
    if not evt:
        await db["stripe_events"].insert_one(event)

    if event["type"] == "checkout.session.completed":
        session: dict = event["data"]["object"]
        await handle_checkout_session_completed(db, settings, session)
    elif event["type"] == "invoice.payment_succeeded":
        invoice: dict = event["data"]["object"]
        await handle_invoice_payment_succeeded(db, invoice)
    elif event["type"] == "invoice.payment_failed":
        invoice: dict = event["data"]["object"]
        await handle_invoice_payment_failed(db, settings, invoice)
    elif event["type"] == "customer.subscription.deleted":
        subscription: dict = event["data"]["object"]
        await handle_subscription_deleted(db, settings, subscription)

    return {"status": "success"}


@webhooks.post("/telegram-webhook")
async def telegram_webhook(
    request: Request, db: AsyncIOMotorDatabase = Depends(get_db), settings: Settings = Depends(get_settings)
) -> dict[str, str]:
    update: dict = await request.json()

    if "chat_join_request" in update:
        await handle_chat_join_request(db, settings, update)

    if "message" in update:
        message: dict = update["message"]
        if message.get("text").lower().strip() in ("/start", "/start@sbatmonitoringbot"):
            response_message: str = (
                f"Hallo {message['from'].get('first_name', 'gebruiker')}, "
                "stuur een /start bericht naar @SbatMonitoringBot in een privégesprek om privé meldingen te ontvangen."
            )
            if message.get("chat").get("type") == "private":
                response_message: str = await handle_start(db, message.get("from"))
            await send_telegram_message(response_message, settings.telegram_bot_token, message.get("chat").get("id"))
        if message.get("text").lower().strip() in ("/voorkeuren", "/voorkeuren@sbatmonitoringbot"):
            response_message: str = (
                f"Hallo {message['from'].get('first_name', 'gebruiker')}, "
                "dit lukt momenteel nog niet via onze telegram bot (@SbatMonitoringBot).\n"
                "Bezoek https://rijexamenmeldingen.be/profile om je voorkeuren aan te passen."
            )
            await send_telegram_message(response_message, settings.telegram_bot_token, message.get("chat").get("id"))

    return {"status": "ok"}
