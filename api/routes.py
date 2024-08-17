import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.models import MonitorStatus

from .dependencies import get_db, get_sbat_monitor
from .models import (
    ExamTimeSlot,
    ExamTimeSlotSchema,
    MonitorConfiguration,
    SbatRequest,
    SbatRequestReadSchema,
    Subscriber,
    SubscriptionRequest,
)
from .sbat_monitor import SbatMonitor

router = APIRouter()


@router.post("/startup", tags=["SBAT monitor"])
async def start_monitoring(config: MonitorConfiguration, sbat_monitor: SbatMonitor = Depends(get_sbat_monitor)) -> dict[str, str]:
    sbat_monitor.config = config
    try:
        await sbat_monitor.start()
        await asyncio.sleep(3)
        if sbat_monitor.task.done() and sbat_monitor.task.exception():
            raise sbat_monitor.task.exception()
        return {"status": "Started successfully"}
    except Exception as e:  # pylint: disable=broad-exception-caught
        return {"status": f"Failed to start monitoring: {str(e)}"}


@router.post("/monitor-config", tags=["SBAT monitor"])
async def update_monitoring_configurations(
    config: MonitorConfiguration, sbat_monitor: SbatMonitor = Depends(get_sbat_monitor)
) -> MonitorStatus:
    sbat_monitor.config = config
    return sbat_monitor.status()


@router.get("/monitor-status", tags=["SBAT monitor"])
async def get_monitoring_status(sbat_monitor: SbatMonitor = Depends(get_sbat_monitor)) -> MonitorStatus:
    return sbat_monitor.status()


@router.get("/shutdown", tags=["SBAT monitor"])
async def stop_monitoring(sbat_monitor: SbatMonitor = Depends(get_sbat_monitor)) -> dict[str, str]:
    try:
        await sbat_monitor.stop()
        return {"status": "Stopped successfully"}
    except Exception as e:  # pylint: disable=broad-exception-caught
        return {"status": f"Failed to stop monitoring: {str(e)}"}


@router.post("/subscribe", tags=["Notification"])
async def subscribe(subscription: SubscriptionRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    existing_subscriber: Subscriber | None = db.query(Subscriber).filter(Subscriber.email == subscription.email).first()
    if existing_subscriber:
        raise HTTPException(status_code=400, detail="Email already subscribed")

    new_subscriber = Subscriber(email=subscription.email)
    db.add(new_subscriber)
    db.commit()
    return {"message": "Subscribed successfully!"}


@router.post("/unsubscribe", tags=["Notification"])
async def unsubscribe(subscription: SubscriptionRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    existing_subscriber: int = db.query(Subscriber).filter(Subscriber.email == subscription.email).delete()
    if existing_subscriber == 0:
        raise HTTPException(status_code=400, detail="Email is not subscribed")
    db.commit()
    return {"message": "Unsubscribed successfully!"}


@router.get("/request", tags=["DB Queries"])
async def get_requests(db: Session = Depends(get_db)) -> list[SbatRequestReadSchema]:
    return db.query(SbatRequest).all()


@router.get("/exam-time-slots", tags=["DB Queries"])
async def get_exam_time_slots(db: Session = Depends(get_db)) -> list[ExamTimeSlotSchema]:
    return db.query(ExamTimeSlot).all()
