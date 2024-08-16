from functools import lru_cache
from typing import Generator

from pydantic_settings import BaseSettings
from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session


class Settings(BaseSettings):
    database_url: str

    sbat_username: str
    sbat_password: str

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    sender_email: str | None = None
    sender_password: str | None = None
    smtp_server: str | None = None
    smtp_port: int | None = None

    google_application_credentials: str | None = None
    database_file: str | None = None
    bucket_name: str | None = None
    blob_name: str | None = None

    class Config:
        env_file: str = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()


engine: Engine = create_engine(get_settings().database_url, connect_args={"check_same_thread": False})
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
