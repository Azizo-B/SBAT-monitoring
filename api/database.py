from datetime import datetime

from sqlalchemy.orm.session import Session

from .models import ExamDate


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


def set_date_status(db: Session, exam_id: str, status: str) -> None:
    db_date: ExamDate | None = db.query(ExamDate).filter(ExamDate.exam_id == exam_id).first()
    if db_date:
        db_date.status = status
        db.commit()
        db.refresh(db_date)
