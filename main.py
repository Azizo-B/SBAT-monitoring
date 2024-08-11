import asyncio

from fastapi import FastAPI
from sqlalchemy.orm.session import Session

from api.dependencies import Base, SessionLocal, engine
from api.routes import router
from api.utils import check_for_dates

app = FastAPI()

Base.metadata.create_all(bind=engine)


@app.on_event("startup")
async def startup_event() -> None:
    db: Session = SessionLocal()
    try:
        print("Database connected on startup")
        asyncio.create_task(check_for_dates(db))
    finally:
        db.close()


app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
