from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from api.dependencies import Settings, client, get_settings
from api.routes import router
from api.utils import send_email


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # pylint: disable=redefined-outer-name, unused-argument
    settings: Settings = get_settings()
    try:
        send_email(
            "test",
            ["aziz.baatout@gmail.com"],
            settings.sender_email,
            settings.sender_password,
            settings.smtp_server,
            settings.smtp_port,
            message="test",
        )
        yield
    finally:
        client.close()


app = FastAPI(title="SBAT Exam Time Slot Checker", lifespan=lifespan)


app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
