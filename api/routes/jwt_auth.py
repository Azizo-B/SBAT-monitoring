from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from motor.motor_asyncio import AsyncIOMotorDatabase

from api.db import mongoDB

from ..dependencies import Settings, get_db, get_settings
from ..models import SubscriberCreate, SubscriberRead
from ..utils import create_access_token

auth = APIRouter(prefix="/auth", tags=["Authentication"])


@auth.post("/signup")
async def subscribe(subscriber: SubscriberCreate, db: AsyncIOMotorDatabase = Depends(get_db)) -> dict[str, str]:
    try:
        await mongoDB.add_subscriber(db, subscriber)
        return {"message": "Subscribed successfully!"}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Email already subscribed") from e


@auth.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncIOMotorDatabase = Depends(get_db), settings: Settings = Depends(get_settings)
) -> dict[str, str]:
    subscriber: SubscriberRead | None = await mongoDB.authenticate_subscriber(db, form_data.username, form_data.password)
    if not subscriber:
        raise HTTPException(status_code=401, detail="Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})

    access_token: str = create_access_token(
        {"sub": subscriber.email}, settings.access_token_expire_minutes, settings.jwt_secret_key, settings.jwt_algorithm
    )
    return {"access_token": access_token, "token_type": "bearer"}
