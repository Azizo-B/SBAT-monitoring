from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .dependencies import get_db
from .models import ExamDate, ExamDateSchema, SbatRequests, SbatRequestSchema, Subscriber, SubscriptionRequest

router = APIRouter()


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
