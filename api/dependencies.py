import os
from functools import lru_cache
from typing import Generator

from pydantic_settings import BaseSettings
from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session


class Settings(BaseSettings):
    telegram_bot_token: str
    telegram_chat_id: str
    sbat_username: str
    sbat_password: str
    database_url: str
    database_file: str
    bucket_name: str
    blob_name: str
    google_application_credentials: str
    sender_email: str | None = None
    sender_password: str | None = None
    smtp_server: str | None = None
    smtp_port: int | None = None

    class Config:
        env_file: str = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()


engine: Engine = create_engine(os.getenv("DATABASE_URL"), connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator:
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@lru_cache
def get_sbat_monitor():
    db: Session = next(get_db())
    settings: Settings = get_settings()

    from .sbat_monitor import SbatMonitor  # pylint: disable=import-outside-toplevel

    return SbatMonitor(db=db, settings=settings)
