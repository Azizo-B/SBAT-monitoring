import datetime

import stripe
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

from ..db.base_repo import BaseRepository
from ..dependencies import get_repo, get_settings
from ..models.common import ReferenceCreate, ReferenceRead
from ..models.settings import Settings
from ..utils import send_telegram_message
from . import discord_handlers
from .stripe_handlers import (
    handle_checkout_session_completed,
    handle_invoice_payment_failed,
    handle_invoice_payment_succeeded,
    handle_subscription_deleted,
)
from .telegram_handlers import handle_start, handle_voorkeuren

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

    if message := update.get("message"):
        input_text: str = message.get("text", "").lower().strip()
        if input_text in ("/start", "/start@sbatmonitoringbot"):
            response: str = await handle_start(repo, message)
            await send_telegram_message(response, settings.telegram_bot_token, message.get("chat").get("id"))
        if input_text in ("/voorkeuren", "/voorkeuren@sbatmonitoringbot"):
            response: str = await handle_voorkeuren(message)
            await send_telegram_message(response, settings.telegram_bot_token, message.get("chat").get("id"))

    return {"status": "ok"}


@webhooks.post("/discord-webhook")
async def discord_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    repo: BaseRepository = Depends(get_repo("mongodb")),
    settings: Settings = Depends(get_settings),
) -> dict:
    body: bytes = await request.body()
    signature: str | None = request.headers.get("X-Signature-Ed25519")
    timestamp: str | None = request.headers.get("X-Signature-Timestamp")
    message: bytes = f"{timestamp}{body.decode('utf-8')}".encode()
    verify_key = VerifyKey(bytes.fromhex(settings.discord_public_key))

    try:
        verify_key.verify(message, bytes.fromhex(signature))
    except BadSignatureError as bse:
        raise HTTPException(status_code=401, detail="Invalid request signature") from bse

    interaction: dict = await request.json()
    command_type: int | None = interaction.get("type")
    command_data: str | None = interaction.get("data", {}).get("name")

    if command_type == 1:
        return {"type": 1}
    elif command_type == 2:
        if command_data == "start":
            response_message: str = await discord_handlers.handle_start(background_tasks, repo, settings, interaction)
            return {"type": 4, "data": {"content": response_message}}
        elif command_data == "voorkeuren":
            response_message: str = await discord_handlers.handle_voorkeuren()
            return {"type": 4, "data": {"content": response_message}}
        else:
            return {"type": 4, "data": {"content": "Unknown command."}}
    else:
        raise HTTPException(status_code=400, detail="Invalid interaction type")


@webhooks.post("/ref-webhook")
async def log_ref(request: Request, repo: BaseRepository = Depends(get_repo("mongodb"))) -> dict[str, str]:
    data: dict = await request.json()
    user_ip: str = request.client.host
    timestamp: str = datetime.datetime.now(datetime.UTC)

    await repo.create(
        "reference_events",
        ReferenceCreate.model_validate(
            {
                "ip": user_ip,
                "body": data,
                "headers": request.headers,
                "timestamp": timestamp,
            }
        ),
        ReferenceRead,
    )
    return {"status": "success"}
