import asyncio
import os
from datetime import datetime
from multiprocessing import AuthenticationError
from typing import NoReturn

import requests
from sqlalchemy.orm.session import Session

from .database import add_date, get_notified_dates, set_date_status

TELEGRAM_BOT_TOKEN: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID: str | None = os.getenv("CHAT_ID")
AUTH_URL: str | None = os.getenv("AUTH_URL")
CHECK_URL: str | None = os.getenv("CHECK_URL")

STANDARD_HEADERS: dict[str, str] = {
    "Cache-Control": "no-cache",
    "Content-Type": "application/json",
    "Accept": "*/*",
    "Connection": "keep-alive",
    "User-Agent": "PostmanRuntime/7.39.1",
    "Accept-Encoding": "gzip, deflate, br",
}


def reauthenticate() -> str:
    auth_response: requests.Response = requests.post(
        AUTH_URL,
        json={"username": os.getenv("SBAT_USERNAME"), "password": os.getenv("SBAT_PASSWORD")},
        headers=STANDARD_HEADERS,
        timeout=1000,
    )
    if auth_response.status_code == 200:
        token: str = auth_response.text
        return token
    else:
        raise AuthenticationError("Authentication failed")


async def check_for_dates(db: Session) -> NoReturn:
    token: str = reauthenticate()
    headers: dict[str, str] = {**STANDARD_HEADERS, "Authorization": f"Bearer {token}"}
    notified_dates: set = get_notified_dates(db)

    while True:
        response: requests.Response = requests.post(
            CHECK_URL,
            headers=headers,
            json={
                "examCenterId": 1,
                "licenseType": "B",
                "examType": "E2",
                "startDate": datetime.combine(datetime.now().date(), datetime.min.time()).isoformat(),
            },
            timeout=1000,
        )
        if response.status_code == 200:
            data: dict = response.json()

            if data:
                update_dates(db, data, notified_dates)

        elif response.status_code == 401:
            headers: dict[str, str] = {**STANDARD_HEADERS, "Authorization": f"Bearer {reauthenticate()}"}

        await asyncio.sleep(600)


def update_dates(db: Session, dates: list[dict], notified_dates: set) -> None:
    current_dates = set()
    message = ""

    for date in dates:
        exam_id: int = date["id"]
        start_time: datetime = datetime.fromisoformat(date["from"])
        end_time: datetime = datetime.fromisoformat(date["till"])
        current_dates.add(exam_id)

        if exam_id not in notified_dates:
            message += f"Date: {start_time.date()} Time: {start_time.time()} - {end_time.time()}\n\n"
            add_date(db, date, status="notified")

    if message:
        message: str = "New driving exam dates available:\n\n" + message
        send_telegram_message(message)

    for exam_id in notified_dates - current_dates:
        set_date_status(db, exam_id, "taken")


def send_telegram_message(message: str) -> None:
    url: str = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload: dict[str, str] = {"chat_id": CHAT_ID, "text": message}
    response: requests.Response = requests.post(url, data=payload, timeout=1000)
    print(response.json())
