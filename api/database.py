from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm.session import Session

from .models import ExamTimeSlot, SbatRequest, Subscriber


def add_time_slot(db: Session, time_slot: dict, status: str) -> ExamTimeSlot:
    db_time_slot = ExamTimeSlot(
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
        types_blob=time_slot["typesBlob"],
    )
    db.add(db_time_slot)
    db.commit()
    db.refresh(db_time_slot)
    return db_time_slot


def get_notified_time_slots(db: Session, exam_center_id: int, license_type: str) -> set:
    return {
        time_slot.exam_id
        for time_slot in db.query(ExamTimeSlot)
        .filter(
            ExamTimeSlot.status == "notified",
            ExamTimeSlot.exam_center_id == exam_center_id,
            ExamTimeSlot.types_blob.like(f"%{license_type}%"),
        )
        .all()
    }


def get_time_slot_status(db: Session, exam_id: str) -> str | None:
    db_time_slot: ExamTimeSlot | None = db.query(ExamTimeSlot).filter(ExamTimeSlot.exam_id == exam_id).first()
    return db_time_slot.status if db_time_slot else None


def set_time_slot_status(db: Session, exam_id: str, status: str) -> None:
    db_time_slot: ExamTimeSlot | None = db.query(ExamTimeSlot).filter(ExamTimeSlot.exam_id == exam_id).first()
    if db_time_slot:
        db_time_slot.status = status
        if status == "taken":
            db_time_slot.taken_at = datetime.now()
        if status == "notified":
            db_time_slot.found_at = datetime.now()
        db.commit()
        db.refresh(db_time_slot)


def set_first_taken_at(db: Session, exam_id: str) -> None:
    db_time_slot: ExamTimeSlot | None = db.query(ExamTimeSlot).filter(ExamTimeSlot.exam_id == exam_id).first()
    if db_time_slot and not db_time_slot.first_taken_at:
        db_time_slot.first_taken_at = datetime.now()
        db.commit()
        db.refresh(db_time_slot)


def get_all_subscribers(db: Session) -> list[str]:
    return [subscriber.email for subscriber in db.query(Subscriber).all()]


def add_sbat_request(
    db: Session,
    email_used: str,
    request_type: str,
    url: str,
    request_body: str | None = None,
    response: str | None = None,
    response_body: str | None = None,
) -> SbatRequest:
    db_request = SbatRequest(
        email_used=email_used,
        request_type=request_type,
        request_body=request_body,
        response=response,
        response_body=response_body,
        url=url,
    )
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    return db_request


def get_last_sbat_auth_request(db: Session) -> SbatRequest | None:
    return db.query(SbatRequest).filter(SbatRequest.request_type == "authentication").order_by(desc(SbatRequest.timestamp)).first()
