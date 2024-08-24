import json
from datetime import UTC, datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCursor, AsyncIOMotorDatabase
from passlib.context import CryptContext
from pymongo import DESCENDING
from pymongo.results import InsertOneResult

from ..models import (
    ExamTimeSlotCreate,
    ExamTimeSlotRead,
    MonitorPreferences,
    SbatRequestCreate,
    SbatRequestRead,
    SubscriberCreate,
    SubscriberRead,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def add_time_slot(db: AsyncIOMotorDatabase, time_slot: dict, status: str) -> ExamTimeSlotRead:
    db_time_slot = ExamTimeSlotCreate(
        exam_id=time_slot["id"],
        start_time=datetime.fromisoformat(time_slot["from"]),
        end_time=datetime.fromisoformat(time_slot["till"]),
        status=status,
        is_public=time_slot["isPublic"],
        day_id=time_slot["dayScheduleId"],
        driving_school=time_slot["drivingSchool"],
        exam_center_id=time_slot["examCenterId"],
        exam_type=time_slot["examType"],
        examinee=time_slot["examinee"],
        types_blob=json.loads(time_slot["typesBlob"]),
    )

    result: InsertOneResult = await db["slots"].insert_one(db_time_slot.model_dump())
    return ExamTimeSlotRead(_id=result.inserted_id, **db_time_slot.model_dump())


async def get_notified_time_slots(db: AsyncIOMotorDatabase, exam_center_id: int, license_type: str) -> set[int]:
    cursor: AsyncIOMotorCursor = db["slots"].find(
        {
            "status": "notified",
            "exam_center_id": exam_center_id,
            "types_blob": {"$in": [license_type]},
        }
    )

    time_slots: set[int] = {slot["exam_id"] async for slot in cursor}
    return time_slots


async def get_time_slot_status(db: AsyncIOMotorDatabase, exam_id: str) -> str | None:
    db_time_slot: dict | None = await db["slots"].find_one({"exam_id": exam_id})
    return db_time_slot["status"] if db_time_slot else None


async def set_time_slot_status(db: AsyncIOMotorDatabase, exam_id: str, status: str) -> None:
    update_fields: dict[str, str] = {"status": status}
    if status == "taken":
        update_fields["taken_at"] = datetime.now(UTC)
    if status == "notified":
        update_fields["found_at"] = datetime.now(UTC)

    await db["slots"].update_one({"exam_id": exam_id}, {"$set": update_fields})


async def set_first_taken_at(db: AsyncIOMotorDatabase, exam_id: str) -> None:
    await db["slots"].update_one(
        {"exam_id": exam_id, "$or": [{"first_taken_at": {"$exists": False}}, {"first_taken_at": False}]},
        {"$set": {"first_taken_at": datetime.now(UTC)}},
    )


async def authenticate_subscriber(db: AsyncIOMotorDatabase, username: str, password: str) -> SubscriberRead | None:
    subscriber: dict | None = await db["subscribers"].find_one({"email": username.lower()})
    if not subscriber or not pwd_context.verify(password, subscriber.get("hashed_password")):
        return

    return SubscriberRead(**subscriber)


async def add_subscriber(db: AsyncIOMotorDatabase, subscriber: SubscriberCreate) -> None:
    subscriber.email = subscriber.email.lower()
    existing_subscriber: dict | None = await db["subscribers"].find_one({"email": subscriber.email})
    if existing_subscriber:
        raise Exception("Email already subscribed")  # pylint: disable=broad-exception-raised

    await db["subscribers"].insert_one(
        {**subscriber.model_dump(exclude="password"), "hashed_password": pwd_context.hash(subscriber.password)}
    )


async def update_subscriber_preferences(db: AsyncIOMotorDatabase, subscriber_id: str, preferences: MonitorPreferences) -> None:
    await db["subscribers"].update_one({"_id": ObjectId(subscriber_id)}, {"$set": {"monitoring_preferences": {**preferences.model_dump()}}})


async def activate_subscription(db: AsyncIOMotorDatabase, stripe_customer_id: str, amount_paid: int) -> None:
    await db["subscribers"].update_one(
        {"stripe_customer_id": stripe_customer_id},
        {
            "$set": {
                "is_subscription_active": True,
            },
            "$inc": {
                "total_spent": amount_paid,
            },
        },
    )


async def deactivate_subscription(db: AsyncIOMotorDatabase, stripe_customer_id) -> None:
    await db["subscribers"].update_one({"stripe_customer_id": stripe_customer_id}, {"$set": {"is_subscription_active": False}})


async def process_checkout_session(db: AsyncIOMotorDatabase, session: dict, telegram_link: str) -> SubscriberRead:
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
    result: InsertOneResult = await db["subscribers"].insert_one({**valid.model_dump(exclude="password"), "hashed_password": ""})
    return SubscriberRead(_id=result.inserted_id, hashed_password="", **valid.model_dump())


async def get_all_subscribed_mails(db: AsyncIOMotorDatabase, exam_center_id: int, license_type: str) -> list[str]:
    cursor: AsyncIOMotorCursor = db["subscribers"].find(
        {"monitoring_preferences.exam_center_ids": exam_center_id, "monitoring_preferences.license_types": license_type}, {"email": 1}
    )
    return [subscriber["email"] async for subscriber in cursor]


async def get_all_telegram_user_ids(db: AsyncIOMotorDatabase, exam_center_id: int, license_type: str) -> list[str]:
    """Retrieve all Telegram user IDs from the database based on exam center and license type."""
    cursor: AsyncIOMotorCursor = db["subscribers"].find(
        {"monitoring_preferences.exam_center_ids": exam_center_id, "monitoring_preferences.license_types": license_type},
        {"telegram_user.id": 1},
    )
    user_ids: list[str] = [subscriber["telegram_user"]["id"] async for subscriber in cursor]
    return user_ids


async def add_sbat_request(
    db: AsyncIOMotorDatabase,
    email_used: str,
    request_type: str,
    url: str,
    request_body: dict | None = None,
    response: dict | None = None,
) -> SbatRequestRead:
    db_request = SbatRequestCreate(
        timestamp=datetime.now(UTC),
        request_type=request_type,
        request_body=request_body,
        response=response,
        url=url,
        email_used=email_used,
    )

    result: InsertOneResult = await db["requests"].insert_one(db_request.model_dump())
    return SbatRequestRead(_id=result.inserted_id, **db_request.model_dump())


async def get_last_sbat_auth_request(db: AsyncIOMotorDatabase) -> SbatRequestRead | None:
    document: dict | None = await db["requests"].find_one({"request_type": "authentication"}, sort=[("timestamp", DESCENDING)])
    if document:
        return SbatRequestRead(**document)
    return None


async def get_subscribers(db: AsyncIOMotorDatabase, limit: int = 10) -> list[SubscriberRead]:
    subscribers: list[SubscriberRead] = []
    async for subscriber in db["subscribers"].find().sort("_id", -1).limit(limit):
        subscribers.append(SubscriberRead.model_validate(subscriber))
    return subscribers


async def get_subscriber(db: AsyncIOMotorDatabase, query: dict) -> SubscriberRead | None:
    subscriber: dict | None = await db["subscribers"].find_one(query)
    if subscriber:
        return SubscriberRead.model_validate(subscriber)


async def get_requests(db: AsyncIOMotorDatabase, limit: int = 10) -> list[SbatRequestRead]:
    requests: list[SbatRequestRead] = []
    async for request in db["requests"].find().sort("_id", -1).limit(limit):
        requests.append(SbatRequestRead.model_validate(request))
    return requests


async def get_time_slots(db: AsyncIOMotorDatabase, limit: int = 10) -> list[ExamTimeSlotRead]:
    time_slots: list[ExamTimeSlotRead] = []
    async for time_slot in db["slots"].find().sort("_id", -1).limit(limit):
        time_slots.append(ExamTimeSlotRead.model_validate(time_slot))
    return time_slots
