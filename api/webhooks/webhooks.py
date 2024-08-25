import stripe
from fastapi import APIRouter, Depends, HTTPException, Request

from ..db.base_repo import BaseRepository
from ..dependencies import get_repo, get_settings
from ..models.settings import Settings
from ..utils import send_telegram_message
from .stripe_handlers import (
    handle_checkout_session_completed,
    handle_invoice_payment_failed,
    handle_invoice_payment_succeeded,
    handle_subscription_deleted,
)
from .telegram_handlers import handle_chat_join_request, handle_start, handle_voorkeuren

webhooks = APIRouter(tags=["Webhooks"])


@webhooks.post("/stripe-webhook")
async def stripe_webhook(
    request: Request, settings: Settings = Depends(get_settings), repo: BaseRepository = Depends(get_repo("mongodb"))
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

    await repo.create_stripe_event(event)

    if event["type"] == "checkout.session.completed":
        session: dict = event["data"]["object"]
        await handle_checkout_session_completed(repo, settings, session)
    elif event["type"] == "invoice.payment_succeeded":
        invoice: dict = event["data"]["object"]
        await handle_invoice_payment_succeeded(repo, invoice)
    elif event["type"] == "invoice.payment_failed":
        invoice: dict = event["data"]["object"]
        await handle_invoice_payment_failed(repo, settings, invoice)
    elif event["type"] == "customer.subscription.deleted":
        subscription: dict = event["data"]["object"]
        await handle_subscription_deleted(repo, settings, subscription)

    return {"status": "success"}


@webhooks.post("/telegram-webhook")
async def telegram_webhook(
    request: Request, repo: BaseRepository = Depends(get_repo("mongodb")), settings: Settings = Depends(get_settings)
) -> dict[str, str]:
    update: dict = await request.json()

    if "chat_join_request" in update:
        await handle_chat_join_request(repo, settings, update)

    if message := update.get("message"):
        input_text: str = message.get("text", "").lower().strip()
        if input_text in ("/start", "/start@sbatmonitoringbot"):
            response: str = await handle_start(repo, message)
            await send_telegram_message(response, settings.telegram_bot_token, message.get("chat").get("id"))
        if input_text in ("/voorkeuren", "/voorkeuren@sbatmonitoringbot"):
            response: str = await handle_voorkeuren(message)
            await send_telegram_message(response, settings.telegram_bot_token, message.get("chat").get("id"))

    return {"status": "ok"}
