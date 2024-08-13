import asyncio
import json
from datetime import datetime
from multiprocessing import AuthenticationError
from typing import NoReturn

import requests
from sqlalchemy.orm.session import Session

from .database import (
    add_date,
    add_sbat_request,
    get_all_subscribers,
    get_date_status,
    get_notified_dates,
    set_date_status,
    set_first_taken_at,
)
from .dependencies import Settings
from .utils import send_email_to, send_telegram_message


class SbatMonitor:

    AUTH_URL = "https://api.rijbewijs.sbat.be/praktijk/api/user/authenticate"
    CHECK_URL = "https://api.rijbewijs.sbat.be/praktijk/api/exam/available"
    STANDARD_HEADERS: dict[str, str] = {
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Connection": "keep-alive",
        "User-Agent": "PostmanRuntime/7.39.1",
        "Accept-Encoding": "gzip, deflate, br",
    }

    def __init__(
        self, db: Session | None = None, settings: Settings | None = None, license_type: str = "B", seconds_inbetween: int = 600
    ) -> None:
        self.db: Session = db
        self.settings: Settings = settings
        self.seconds_inbetween: int = seconds_inbetween
        self.license_type: str = license_type
        self.task: asyncio.Task | None = None

    async def start(self) -> None:
        if self.task:
            raise RuntimeError("Monitoring is already running.")
        self.task = asyncio.create_task(self.check_for_dates())

    async def stop(self) -> None:
        if not self.task or self.task.done():
            raise RuntimeError("Monitoring is not running.")
        self.task.cancel()
        try:
            await self.task
        except asyncio.CancelledError:
            pass
        self.task = None

    def authenticate(self) -> str:
        auth_response: requests.Response = requests.post(
            self.AUTH_URL,
            json={"username": self.settings.sbat_username, "password": self.settings.sbat_password},
            headers=self.STANDARD_HEADERS,
            timeout=1000,
        )

        add_sbat_request(self.db, self.settings.sbat_username, "authentication", url=self.AUTH_URL, response=auth_response.status_code)

        if auth_response.status_code == 200:
            token: str = auth_response.text
            return token
        else:
            raise AuthenticationError("Authentication failed")

    async def check_for_dates(self) -> NoReturn:
        token: str = self.authenticate()
        headers: dict[str, str] = {**self.STANDARD_HEADERS, "Authorization": f"Bearer {token}"}

        while True:
            print("Checking for new dates...")
            body: dict = {
                "examCenterId": 1,
                "licenseType": self.license_type,
                "examType": "E2",
                "startDate": datetime.combine(datetime.now().date(), datetime.min.time()).isoformat(),
            }
            response: requests.Response = requests.post(
                self.CHECK_URL,
                headers=headers,
                json=body,
                timeout=1000,
            )

            add_sbat_request(
                self.db, self.settings.sbat_username, "check_for_dates", self.CHECK_URL, json.dumps(body), response.status_code
            )
            print(f"Response status code {response.status_code}")

            if response.status_code == 200:
                data: dict = response.json()
                print(data)
                self.notify_users_and_update_db(data)

            elif response.status_code == 401:
                headers: dict[str, str] = {**self.STANDARD_HEADERS, "Authorization": f"Bearer {self.authenticate()}"}
                continue

            await asyncio.sleep(self.seconds_inbetween)

    def notify_users_and_update_db(self, dates: list[dict]) -> None:
        current_dates = set()
        notified_dates: set = get_notified_dates(self.db)
        message = ""

        for date in dates:
            exam_id: int = date["id"]
            start_time: datetime = datetime.fromisoformat(date["from"])
            end_time: datetime = datetime.fromisoformat(date["till"])
            current_dates.add(exam_id)

            if exam_id not in notified_dates:

                new_date_messag: str = f"Date: {start_time.date()} Time: {start_time.time()} - {end_time.time()}\n"
                if new_date_messag not in message:
                    message += new_date_messag

                if get_date_status(self.db, exam_id) == "taken":
                    set_date_status(self.db, exam_id, "notified")
                else:
                    add_date(self.db, date, status="notified")

        if message:
            subject: str = f"New driving exam dates available for license type '{self.license_type}':"
            message: str = subject + "\n\n" + message
            send_email_to(
                subject,
                message,
                get_all_subscribers(self.db),
                self.settings.sender_email,
                self.settings.sender_password,
                self.settings.smtp_server,
                self.settings.smtp_port,
            )
            send_telegram_message(message, self.settings.telegram_bot_token, self.settings.telegram_chat_id)

        for exam_id in notified_dates - current_dates:
            set_date_status(self.db, exam_id, "taken")
            set_first_taken_at(self.db, exam_id)