from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from api.dependencies import Base, Settings, engine, get_settings
from api.routes import router
from api.utils import download_file_from_gcs, upload_file_to_gcs


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # pylint: disable=redefined-outer-name, unused-argument
    try:
        settings: Settings = get_settings()
        download_file_from_gcs(settings.bucket_name, settings.blob_name, settings.database_file)
        Base.metadata.create_all(bind=engine)
        yield
    finally:
        upload_file_to_gcs(settings.bucket_name, settings.blob_name, settings.database_file)


app = FastAPI(title="SBAT Exam Date Checker", lifespan=lifespan)


app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
