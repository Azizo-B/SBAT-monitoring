import stripe
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from api import database

from .dependencies import Settings, get_db, get_settings
from .models import SubscriberCreate, SubscriberRead
from .utils import create_single_use_invite_link, send_email

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
    elif event["type"] == "invoice.payment_succeeded":
        invoice: dict = event["data"]["object"]
        await handle_invoice_payment_succeeded(db, invoice)
    elif event["type"] == "invoice.payment_failed":
        invoice: dict = event["data"]["object"]
        await handle_invoice_payment_failed(db, settings, invoice)
    elif event["type"] == "customer.subscription.deleted":
        subscription: dict = event["data"]["object"]
        await deactivate_subscription(db, settings, subscription)

    return {"status": "success"}


async def handle_invoice_payment_failed(db: AsyncIOMotorDatabase, settings: Settings, invoice: dict) -> None:
    stripe_customer_id: str = invoice.get("customer")
    user: dict | None = await db["subscribers"].find_one({"stripe_customer_id": stripe_customer_id})
    if not user:
        print(f"No user found with Stripe customer ID: {stripe_customer_id}")
        return

    await db["subscribers"].update_one(
        {"_id": user["_id"]},
        {"$set": {"is_subscription_active": False}},
    )
    send_email(
        "Betalingsfout - Actie Vereist",
        [user["email"]],
        settings.sender_email,
        settings.sender_password,
        settings.smtp_server,
        settings.smtp_port,
        is_html=True,
        html_template="payment_failed_email.html",
        naam=user["name"],
    )
    print(f"Payment failed for user: {user['email']}")


async def handle_invoice_payment_succeeded(db: AsyncIOMotorDatabase, invoice: dict) -> None:
    stripe_customer_id: str = invoice.get("customer")
    amount_paid: int = invoice.get("amount_paid")
    user: dict | None = await db["subscribers"].find_one({"stripe_customer_id": stripe_customer_id})
    if not user:
        print(f"No user found with Stripe customer ID: {stripe_customer_id}")
        return

    await db["subscribers"].update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "is_subscription_active": True,
                "total_spent": user.get("total_spent", 0) + amount_paid,
            }
        },
    )
    print(f"Payment succeeded for user: {user['email']}, amount: {amount_paid}")


async def deactivate_subscription(db: AsyncIOMotorDatabase, settings: Settings, subscription: dict) -> None:
    stripe_customer_id: str = subscription.get("customer")
    await db["subscribers"].update_one({"stripe_customer_id": stripe_customer_id}, {"$set": {"is_subscription_active": False}})
    user: dict | None = await db["subscribers"].find_one({"stripe_customer_id": stripe_customer_id})
    send_email(
        "Bevestiging van Annulering van je Abonnement.",
        [user["email"]],
        settings.sender_email,
        settings.sender_password,
        settings.smtp_server,
        settings.smtp_port,
        is_html=True,
        html_template="cancellation_email.html",
        naam=user["name"],
    )


async def handle_payment_link_session(db: AsyncIOMotorDatabase, settings: Settings, session: dict) -> None:
    telegram_link: str | None = await create_single_use_invite_link(settings.telegram_chat_id, settings.telegram_bot_token)
    user: SubscriberRead = await add_new_customer_from_session(db, session, telegram_link)
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


async def add_new_customer_from_session(db: AsyncIOMotorDatabase, session: dict, telegram_link: str) -> SubscriberRead:
    sub_id: str = session.get("subscription")
    amount_total: int = session.get("amount_total")
    client_reference_id: str = session.get("client_reference_id")
    stripe_customer_id: str = session.get("customer")

    customer_details: dict = session.get("customer_details", {})
    name: str = customer_details.pop("name")
    email: str = customer_details.pop("email")
    phone: str = customer_details.pop("phone")

    existing_user: dict | None = await db["subscribers"].find_one({"_id": ObjectId(client_reference_id)})
    if existing_user:
        valid: SubscriberRead = SubscriberRead.model_validate(existing_user)
        if sub_id not in valid.stripe_ids:
            valid.stripe_ids.append(sub_id)

        await db["subscribers"].update_one(
            {"_id": existing_user.get("_id")},
            {
                "$set": {
                    "stripe_ids": valid.stripe_ids,
                    "phone": phone,
                    "name": name,
                    "extra_details": customer_details,
                    "stripe_customer_id": stripe_customer_id,
                    "is_subscription_active": True,
                    "telegram_link": valid.telegram_link if valid.telegram_link else telegram_link,
                }
            },
        )
        return valid

    valid = SubscriberCreate(
        stripe_ids=[sub_id],
        stripe_customer_id=stripe_customer_id,
        is_subscription_active=True,
        telegram_link=telegram_link,
        name=name,
        email=email,
        phone=phone,
        total_spent=amount_total,
        extra_details=customer_details,
        password="",
    )
    result: database.InsertOneResult = await db["subscribers"].insert_one({**valid.model_dump(exclude="password"), "hashed_password": ""})
    return SubscriberRead(_id=result.inserted_id, hashed_password="", **valid.model_dump())
