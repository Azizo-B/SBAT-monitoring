from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from ..db.base_repo import BaseRepository
from ..dependencies import get_repo, get_settings
from ..models.settings import Settings
from ..models.subscriber import SubscriberCreate, SubscriberRead
from ..utils import create_access_token, send_email

auth = APIRouter(prefix="/auth", tags=["Authentication"])


@auth.post("/signup")
async def subscribe(
    subscriber: SubscriberCreate, repo: BaseRepository = Depends(get_repo("mongodb")), settings: Settings = Depends(get_settings)
) -> dict[str, str]:
    try:
        await repo.create_subscriber(subscriber)
        send_email(
            "Verify your email",
            [subscriber.email],
            settings.sender_email,
            settings.sender_password,
            settings.smtp_server,
            settings.smtp_port,
            is_html=True,
            html_template="email_verification.html",
            naam=subscriber.name,
            verification_token=subscriber.verification_token,
        )
        return {"message": "Subscribed successfully! Please check your email to verify your account."}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail="Email already subscribed") from e


@auth.get("/verify")
async def verify_email(verification_token: str, repo: BaseRepository = Depends(get_repo("mongodb"))) -> dict[str, str]:
    subscriber: SubscriberRead | None = await repo.find_one("subscribers", {"verification_token": verification_token}, SubscriberRead)
    if not subscriber:
        raise HTTPException(status_code=400, detail="Invalid token")

    if subscriber.is_verified:
        return {"message": "Email already verified"}

    await repo.update_one("subscribers", {"email": subscriber.email}, {"is_verified": True}, SubscriberRead)

    return {"message": "Email verified successfully!"}


@auth.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    repo: BaseRepository = Depends(get_repo("mongodb")),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    subscriber: SubscriberRead | None = await repo.verify_subscriber_credentials(form_data.username, form_data.password)
    if not subscriber:
        raise HTTPException(status_code=401, detail="Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})

    if not subscriber.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified", headers={"WWW-Authenticate": "Bearer"})

    access_token: str = create_access_token(
        {"sub": subscriber.email}, settings.access_token_expire_minutes, settings.jwt_secret_key, settings.jwt_algorithm
    )
    return {"access_token": access_token, "token_type": "bearer"}
