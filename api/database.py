from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm.session import Session

from .models import ExamDate, SbatRequest, Subscriber


def add_date(db: Session, date: dict, status: str) -> ExamDate:
    db_date = ExamDate(
        exam_id=date["id"],
        start_time=datetime.fromisoformat(date["from"]),
        end_time=datetime.fromisoformat(date["till"]),
        status=status,
        is_public=date["isPublic"],
        day_id=date["dayScheduleId"],
        driving_school=date["drivingSchool"],
        exam_center_id=date["examCenterId"],
        exam_type=date["examType"],
        examinee=date["examinee"],
        types_blob=date["typesBlob"],
    )
    db.add(db_date)
    db.commit()
    db.refresh(db_date)
    return db_date


def get_notified_dates(db: Session) -> set:
    return {date.exam_id for date in db.query(ExamDate).filter(ExamDate.status == "notified").all()}


def get_date_status(db: Session, exam_id: str) -> str | None:
    db_date: ExamDate | None = db.query(ExamDate).filter(ExamDate.exam_id == exam_id).first()
    return db_date.status if db_date else None


def set_date_status(db: Session, exam_id: str, status: str) -> None:
    db_date: ExamDate | None = db.query(ExamDate).filter(ExamDate.exam_id == exam_id).first()
    if db_date:
        db_date.status = status
        if status == "taken":
            db_date.taken_at = datetime.now()
        if status == "notified":
            db_date.found_at = datetime.now()
        db.commit()
        db.refresh(db_date)


def set_first_taken_at(db: Session, exam_id: str) -> None:
    db_date: ExamDate | None = db.query(ExamDate).filter(ExamDate.exam_id == exam_id).first()
    if db_date and not db_date.first_taken_at:
        db_date.first_taken_at = datetime.now()
        db.commit()
        db.refresh(db_date)


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
