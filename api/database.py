import json
from datetime import UTC, datetime

from motor.motor_asyncio import AsyncIOMotorCursor, AsyncIOMotorDatabase
from pymongo import DESCENDING
from pymongo.results import InsertOneResult

from .models import ExamTimeSlotCreate, ExamTimeSlotRead, SbatRequestCreate, SbatRequestRead, SubscriberRead


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


async def get_time_slots(db: AsyncIOMotorDatabase) -> list[ExamTimeSlotRead]:
    time_slots: list[ExamTimeSlotRead] = []
    async for time_slot in db["slots"].find():
        time_slots.append(ExamTimeSlotRead.model_validate(time_slot))
    return time_slots


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


async def get_subscribers(db: AsyncIOMotorDatabase) -> list[SubscriberRead]:
    subscribers: list[SubscriberRead] = []
    async for subscriber in db["subscribers"].find():
        subscribers.append(SubscriberRead.model_validate(subscriber))
    return subscribers


async def get_all_subscribed_mails(db: AsyncIOMotorDatabase) -> list[str]:
    cursor: AsyncIOMotorCursor = db["subscribers"].find({}, {"email": 1})
    return [subscriber["email"] async for subscriber in cursor]


async def add_sbat_request(
    db: AsyncIOMotorDatabase,
    email_used: str,
    request_type: str,
    url: str,
    request_body: dict | None = None,
    response: str | None = None,
    response_body: dict | None = None,
) -> SbatRequestRead:
    db_request = SbatRequestCreate(
        timestamp=datetime.now(UTC),
        request_type=request_type,
        request_body=request_body,
        response=response,
        url=url,
        email_used=email_used,
        response_body=response_body,
    )

    result: InsertOneResult = await db["requests"].insert_one(db_request.model_dump())
    return SbatRequestRead(_id=result.inserted_id, **db_request.model_dump())


async def get_requests(db: AsyncIOMotorDatabase) -> list[SbatRequestRead]:
    requests: list[SbatRequestRead] = []
    async for request in db["requests"].find():
        requests.append(SbatRequestRead.model_validate(request))
    return requests


async def get_last_sbat_auth_request(db: AsyncIOMotorDatabase) -> SbatRequestRead | None:
    document: dict | None = await db["requests"].find_one({"request_type": "authentication"}, sort=[("timestamp", DESCENDING)])
    if document:
        return SbatRequestRead(**document)
    return None
