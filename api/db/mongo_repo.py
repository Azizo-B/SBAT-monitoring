from datetime import UTC, datetime
from typing import Type

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCursor, AsyncIOMotorDatabase
from passlib.context import CryptContext
from pydantic import BaseModel
from pymongo import DESCENDING
from pymongo.results import InsertOneResult

from ..models.sbat import ExamTimeSlotRead, SbatRequestRead
from ..models.subscriber import SubscriberCreate, SubscriberRead
from .base_repo import BaseRepository

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class MongoRepository(BaseRepository):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db: AsyncIOMotorDatabase = db

    async def create(self, table_or_collection: str, data_model: BaseModel, pydantic_return_model: Type[BaseModel]) -> BaseModel:
        result: InsertOneResult = await self.db[table_or_collection].insert_one(data_model.model_dump())
        return pydantic_return_model.model_validate({"_id": result.inserted_id, **data_model.model_dump()})

    async def find(self, table_or_collection: str, query_dict: dict, pydantic_return_model: BaseModel) -> list[BaseModel]:
        results: list = await self.db[table_or_collection].find(query_dict).to_list(None)
        return [pydantic_return_model.model_validate(doc) for doc in results]

    async def find_one(self, table_or_collection: str, query_dict: dict, pydantic_return_model: BaseModel) -> BaseModel | None:
        doc: dict | None = await self.db[table_or_collection].find_one(query_dict)
        if doc:
            return pydantic_return_model.model_validate(doc)

    async def update_one(
        self, table_or_collection: str, query_dict: dict, update_dict: dict, pydantic_return_model: Type[BaseModel]
    ) -> BaseModel | None:
        result: dict | None = await self.db[table_or_collection].find_one_and_update(
            query_dict,
            {"$set": update_dict},
            return_document=True,
        )
        return pydantic_return_model.model_validate(result) if result else None

    # TIME_SLOTS
    async def find_notified_time_slot_ids(self, exam_center_id: int, license_type: str) -> set[int]:
        cursor: AsyncIOMotorCursor = self.db["slots"].find(
            {"status": "notified", "exam_center_id": exam_center_id, "types_blob": {"$in": [license_type]}}
        )
        return {slot["exam_id"] async for slot in cursor}

    async def update_time_slot_status(self, sbat_exam_id: int, status: str) -> ExamTimeSlotRead | None:
        update_fields: dict[str, str] = {"status": status}
        if status == "taken":
            update_fields["taken_at"] = datetime.now(UTC)
        if status == "notified":
            update_fields["found_at"] = datetime.now(UTC)

        time_slot: dict | None = await self.db["slots"].find_one_and_update(
            {"exam_id": sbat_exam_id}, {"$set": update_fields}, return_document=True
        )
        return ExamTimeSlotRead.model_validate(time_slot) if time_slot else None

    # REQUESTS
    async def find_last_sbat_auth_request(self) -> SbatRequestRead | None:
        document: dict | None = await self.db["requests"].find_one({"request_type": "authentication"}, sort=[("timestamp", DESCENDING)])
        return SbatRequestRead.model_validate(document) if document else None

    # SUBSCRIBERS
    async def create_subscriber(self, subscriber: SubscriberCreate) -> SubscriberRead:
        subscriber.email = subscriber.email.lower()
        existing_subscriber: dict | None = await self.db["subscribers"].find_one({"email": subscriber.email})
        if existing_subscriber:
            raise Exception("Email already subscribed")  # pylint: disable=broad-exception-raised

        result: InsertOneResult = await self.db["subscribers"].insert_one(
            {**subscriber.model_dump(exclude="password"), "hashed_password": pwd_context.hash(subscriber.password)}
        )
        return SubscriberRead(_id=result.inserted_id, **subscriber.model_dump())

    async def verify_subscriber_credentials(self, username: str, password: str) -> SubscriberRead | None:
        subscriber: dict | None = await self.db["subscribers"].find_one({"email": username.lower()})
        if not subscriber or not pwd_context.verify(password, subscriber.get("hashed_password")):
            return
        return SubscriberRead.model_validate(subscriber)

    async def find_subscriber_by_telegram_user_id(self, telegram_user_id: int) -> SubscriberRead | None:
        subscriber: dict | None = await self.db["subscribers"].find_one({"telegram_user.id": telegram_user_id})
        if subscriber:
            return SubscriberRead.model_validate(subscriber)

    async def find_all_subscribed_emails(self, exam_center_id: int, license_type: str) -> set[str]:
        cursor: AsyncIOMotorCursor = self.db["subscribers"].find(
            {
                "is_subscription_active": True,
                "monitoring_preferences.exam_center_ids": exam_center_id,
                "monitoring_preferences.license_types": license_type,
            },
            {"email": 1},
        )
        return {subscriber["email"] async for subscriber in cursor}

    async def find_all_subscribed_telegram_ids(self, exam_center_id: int, license_type: str) -> set[int]:
        cursor: AsyncIOMotorCursor = self.db["subscribers"].find(
            {
                "is_subscription_active": True,
                "monitoring_preferences.exam_center_ids": exam_center_id,
                "monitoring_preferences.license_types": license_type,
            },
            {"telegram_user.id": 1, "_id": 0},
        )
        return {subscriber.get("telegram_user").get("id") async for subscriber in cursor if subscriber.get("telegram_user").get("id")}

    async def activate_subscriber_subscription(self, stripe_customer_id: str, amount_paid: int) -> SubscriberRead | None:
        subscriber: dict | None = await self.db["subscribers"].find_one_and_update(
            {"stripe_customer_id": stripe_customer_id},
            {"$set": {"is_subscription_active": True}, "$inc": {"total_spent": amount_paid}},
        )
        return SubscriberRead.model_validate(subscriber) if subscriber else None

    async def process_checkout_session(self, session: dict, telegram_link: str) -> SubscriberRead:
        sub_id: str = session.get("subscription")
        amount_total: int = session.get("amount_total")
        client_reference_id: str = session.get("client_reference_id")
        stripe_customer_id: str = session.get("customer")

        customer_details: dict = session.get("customer_details", {})
        name: str = customer_details.pop("name")
        email: str = customer_details.pop("email")
        phone: str = customer_details.pop("phone")

        existing_user: dict | None = await self.db["subscribers"].find_one({"_id": ObjectId(client_reference_id)})
        if existing_user:
            valid: SubscriberRead = SubscriberRead.model_validate(existing_user)
            if sub_id not in valid.stripe_ids:
                valid.stripe_ids.append(sub_id)

            updated_valid: dict = await self.db["subscribers"].find_one_and_update(
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
                return_document=True,
            )
            return SubscriberRead.model_validate(updated_valid)

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
        result: InsertOneResult = await self.db["subscribers"].insert_one({**valid.model_dump(exclude="password"), "hashed_password": ""})
        return SubscriberRead(_id=result.inserted_id, hashed_password="", **valid.model_dump())

    async def create_stripe_event(self, stripe_event: dict) -> None:
        evt: dict | None = await self.db["stripe_events"].find_one({"id": stripe_event["id"]})
        if not evt:
            await self.db["stripe_events"].insert_one(stripe_event)

    async def create_telegram_event(self, telegram_event: dict) -> None:
        upt: dict | None = await self.db["telegram_events"].find_one({"update_id": telegram_event.get("update_id")})
        if not upt:
            await self.db["telegram_events"].insert_one(telegram_event)
