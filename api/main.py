from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.dependencies import client
from api.routes.jwt_auth import auth
from api.routes.sbat import router as sbat_router
from api.routes.subscribers import router as subscribers_router
from api.routes.temporary import router as temp_router
from api.webhooks.webhooks import webhooks


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # pylint: disable=redefined-outer-name, unused-argument
    try:
        yield
    finally:
        client.close()


app = FastAPI(title="Exam Time Slot Checker", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://localhost:8000", "https://rijexamenmeldingen.be"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(temp_router)
app.include_router(auth)
app.include_router(subscribers_router)
app.include_router(sbat_router)
app.include_router(webhooks)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
