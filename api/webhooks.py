import httpx
import stripe
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from api import database

from .dependencies import Settings, get_db, get_settings
from .models import EXAM_CENTER_MAP, MonitorPreferences, SubscriberCreate, SubscriberRead
from .utils import send_email

webhooks = APIRouter()


@webhooks.post("/payment-link-webhook", tags=["Stripe"])
async def stripe_webhook(
    request: Request, settings: Settings = Depends(get_settings), db: AsyncIOMotorDatabase = Depends(get_db)
) -> dict[str, str]:
    print("webhookk")
    stripe.api_key = settings.stripe_secret_key

    payload: bytes = await request.body()
    sig_header: str | None = request.headers.get("stripe-signature")

    try:
        event: stripe.Event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe_endpoint_secret)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload") from e
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature") from e

    if event["type"] == "checkout.session.completed":
        session: dict = event["data"]["object"]
        await handle_payment_link_session(db, settings, session)

    return {"status": "success"}


async def handle_payment_link_session(db: AsyncIOMotorDatabase, settings: Settings, session: dict):
    user: SubscriberRead = await add_new_customer_from_session(db, session)
    telegram_link: str | None = await create_single_use_invite_link(settings.telegram_chat_id, settings.telegram_bot_token, user.name)
    send_email(
        "Betaling geslaagd! Uw voorkeuren zijn ontvangen.",
        [user.email],
        settings.sender_email,
        settings.sender_password,
        settings.smtp_server,
        settings.smtp_port,
        is_html=True,
        html_template="confirmation_email.html",
        naam=user.name,
        telegram_link=telegram_link,
    )


async def create_single_use_invite_link(chat_id: str, bot_token: str, name: str = None) -> str | None:
    """Create a single-use invite link for a Telegram chat."""
    url: str = f"https://api.telegram.org/bot{bot_token}/createChatInviteLink"
    payload: dict = {
        "chat_id": chat_id,
        "name": name,
        "member_limit": 1,
        "creates_join_request": False,
    }
    async with httpx.AsyncClient() as client:
        response: httpx.Response = await client.post(url, json=payload)
        if response.status_code == 200:
            data: dict = response.json()
            return data["result"]["invite_link"]
        else:
            print(f"Failed to create invite link. Response: {response.text}")
            return None


async def add_new_customer_from_session(db: AsyncIOMotorDatabase, session: dict) -> SubscriberRead:
    session_id: str = session.get("id")
    amount_total: int = session.get("amount_total")
    client_reference_id: str = session.get("client_reference_id")
    print("REFERENCE IDDDDDDDDD", client_reference_id)

    customer_details: dict = session.get("customer_details", {})
    name: str = customer_details.pop("name")
    email: str = customer_details.pop("email")
    phone: str = customer_details.pop("phone")

    custom_fields: list = session.get("custom_fields", [])
    field_dict: dict = {field["key"]: field for field in custom_fields}

    examencentra: str = field_dict.get("examencentralateraantepassentoetevoegen", {}).get("dropdown", {}).get("value", "")
    license_types: list[str] = [field_dict.get("rijbewijslateraantepassentoetevoegen", {}).get("dropdown", {}).get("value", "").upper()]
    telegram_username: str = field_dict.get("telegramusername", {}).get("text", {}).get("value", "")

    exam_center_ids: list[int] = [k for k, v in EXAM_CENTER_MAP.items() if v == examencentra]

    mp = MonitorPreferences(license_types=license_types, exam_center_ids=exam_center_ids)

    existing_user: dict | None = await db["subscribers"].find_one({"_id": ObjectId(client_reference_id)})
    if existing_user:
        valid: SubscriberRead = SubscriberRead.model_validate(existing_user)
        valid.total_spent = valid.total_spent + amount_total
        valid.stripe_ids.append(session_id)
        valid.name = name
        await db["subscribers"].update_one(
            {"_id": existing_user.get("_id")},
            {
                "$set": {
                    "total_spent": valid.total_spent,
                    "stripe_ids": valid.stripe_ids,
                    "phone": phone,
                    "name": name,
                    "telegram_username": telegram_username,
                    "extra_details": customer_details,
                    "monitoring_preferences": {**mp.model_dump()},
                }
            },
        )
        return valid

    valid = SubscriberCreate(
        stripe_ids=[session_id],
        name=name,
        telegram_username=telegram_username,
        email=email,
        phone=phone,
        total_spent=amount_total,
        extra_details=customer_details,
        monitoring_preferences=mp,
        password="",
    )
    result: database.InsertOneResult = await db["subscribers"].insert_one(valid.model_dump())
    return SubscriberRead(_id=result.inserted_id, **valid.model_dump())
