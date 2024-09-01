from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from ..db.base_repo import BaseRepository
from ..dependencies import get_repo, get_settings
from ..models.settings import Settings
from ..models.subscriber import SubscriberCreate, SubscriberRead
from ..utils import create_access_token

auth = APIRouter(prefix="/auth", tags=["Authentication"])


@auth.post("/signup")
async def subscribe(subscriber: SubscriberCreate, repo: BaseRepository = Depends(get_repo("mongodb"))) -> dict[str, str]:
    try:
        await repo.create_subscriber(subscriber)
        return {"message": "Subscribed successfully!"}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail="Email already subscribed") from e


@auth.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    repo: BaseRepository = Depends(get_repo("mongodb")),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    subscriber: SubscriberRead | None = await repo.verify_subscriber_credentials(form_data.username, form_data.password)
    if not subscriber:
        raise HTTPException(status_code=401, detail="Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})

    access_token: str = create_access_token(
        {"sub": subscriber.email}, settings.access_token_expire_minutes, settings.jwt_secret_key, settings.jwt_algorithm
    )
    return {"access_token": access_token, "token_type": "bearer"}
