from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .dependencies import Settings, get_db, get_settings
from .models import ExamDate, ExamDateSchema, SbatRequests, SbatRequestSchema, Subscriber, SubscriptionRequest
from .sbat_monitor import SbatMonitor

router = APIRouter()
sbat_monitor = SbatMonitor()


@router.get("/startup")
async def start_monitoring(
    seconds_inbetween: int | None = None,
    license_type: str | None = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    sbat_monitor.db = db
    sbat_monitor.settings = settings
    sbat_monitor.seconds_inbetween = seconds_inbetween
    sbat_monitor.license_type = license_type

    try:
        await sbat_monitor.start()
        return {"status": "Started successfully"}
    except Exception as e:  # pylint: disable=broad-exception-caught
        return {"status": f"Failed to start monitoring: {str(e)}"}


@router.get("/shutdown")
async def stop_monitoring() -> dict[str, str]:
    try:
        await sbat_monitor.stop()
        return {"status": "Stopped successfully"}
    except Exception as e:  # pylint: disable=broad-exception-caught
        return {"status": f"Failed to stop monitoring: {str(e)}"}


@router.post("/subscribe")
async def subscribe(subscription: SubscriptionRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    existing_subscriber: Subscriber | None = db.query(Subscriber).filter(Subscriber.email == subscription.email).first()
    if existing_subscriber:
        raise HTTPException(status_code=400, detail="Email already subscribed")

    new_subscriber = Subscriber(email=subscription.email)
    db.add(new_subscriber)
    db.commit()
    return {"message": "Subscribed successfully!"}


@router.post("/unsubscribe")
async def unsubscribe(subscription: SubscriptionRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    existing_subscriber: int = db.query(Subscriber).filter(Subscriber.email == subscription.email).delete()
    if existing_subscriber == 0:
        raise HTTPException(status_code=400, detail="Email is not subscribed")
    db.commit()
    return {"message": "Unsubscribed successfully!"}


@router.get("/request")
async def get_requests(db: Session = Depends(get_db)) -> list[SbatRequestSchema]:
    return db.query(SbatRequests).all()


@router.get("/exam-dates")
async def get_exam_dates(db: Session = Depends(get_db)) -> list[ExamDateSchema]:
    return db.query(ExamDate).all()
