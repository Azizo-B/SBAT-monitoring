import asyncio

from dotenv import load_dotenv

load_dotenv()
# pylint: disable=wrong-import-position


from fastapi import FastAPI
from sqlalchemy.orm.session import Session

from api.dependencies import Base, SessionLocal, engine
from api.routes import router
from api.utils import check_for_dates, download_db, upload_db

app = FastAPI(title="SBAT Driving Exam Date Checker")


@app.on_event("startup")
async def startup_event() -> None:
    download_db()
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        print("Database connected on startup")
        asyncio.create_task(check_for_dates(db))
    finally:
        db.close()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    upload_db()


app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
