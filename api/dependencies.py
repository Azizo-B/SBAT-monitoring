import os
from typing import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

engine: Engine = create_engine(os.getenv("DATABASE_URL"), connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator:
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
