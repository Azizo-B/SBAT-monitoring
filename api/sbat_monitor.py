import asyncio
import json
from datetime import datetime, timedelta
from multiprocessing import AuthenticationError
from typing import NoReturn

import jwt
import requests
from sqlalchemy.orm.session import Session

from api.models import SbatRequest

from .database import (
    add_sbat_request,
    add_time_slot,
    get_all_subscribers,
    get_last_sbat_auth_request,
    get_notified_time_slots,
    get_time_slot_status,
    set_first_taken_at,
    set_time_slot_status,
)
from .dependencies import Settings
from .models import MonitorStatus
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
        self, db: Session | None = None, settings: Settings | None = None, license_types: list | None = None, seconds_inbetween: int = 600
    ) -> None:
        self.db: Session = db
        self.settings: Settings = settings
        self.seconds_inbetween: int = seconds_inbetween
        if license_types is None:
            license_types = ["B"]
        self.license_types: list[str] = license_types

        self.task: asyncio.Task | None = None
        self.total_time_running: timedelta = timedelta()
        self.first_started_at: datetime | None = None
        self.last_started_at: datetime | None = None
        self.last_stopped_at: datetime | None = None

    async def start(self) -> None:
        if self.task:
            raise RuntimeError("Monitoring is already running.")
        self.task = asyncio.create_task(self.check_for_time_slots())
        self.last_started_at: datetime = datetime.now()
        self.first_started_at: datetime = self.first_started_at or self.last_started_at
        self.task.add_done_callback(self.clean_up)

    async def stop(self) -> None:
        if not self.task or self.task.done():
            raise RuntimeError("Monitoring is not running.")
        self.task.cancel()
        try:
            await self.task
        except asyncio.CancelledError:
            pass

    def clean_up(self, task: asyncio.Task) -> None:
        if task.cancelled():
            print("SBAT MONITOR STOPPED: Task was cancelled.")
        elif task.done():
            exception: BaseException | None = task.exception()
            if exception:
                print("SBAT MONITOR STOPPED: Exception occurred:", exception)
            else:
                print("SBAT MONITOR STOPPED: Task completed successfully.")

        self.last_stopped_at = datetime.now()
        if self.last_started_at:
            self.total_time_running += self.last_stopped_at - self.last_started_at
        self.task = None

    def status(self) -> MonitorStatus:
        if self.task and not self.task.done():
            current_time: datetime = datetime.now()
            running_time: timedelta = (current_time - self.last_started_at) if self.last_started_at else timedelta()
            total_time_running: timedelta = self.total_time_running + running_time
        else:
            total_time_running: timedelta = self.total_time_running

        return MonitorStatus(
            running=self.task is not None and not self.task.done(),
            seconds_inbetween=self.seconds_inbetween,
            license_types=self.license_types,
            task_done=self.task.done() if self.task else None,
            total_time_running=str(total_time_running),
            first_started_at=self.first_started_at,
            last_started_at=self.last_started_at,
            last_stopped_at=self.last_stopped_at,
            task_exception=str(self.task.exception()) if self.task and self.task.done() and self.task.exception() else None,
        )

    def authenticate(self) -> str:
        last_request: SbatRequest | None = get_last_sbat_auth_request(self.db)
        if last_request:
            try:
                payload: dict = jwt.decode(last_request.response_body, options={"verify_signature": False})
                if datetime.now() < datetime.fromtimestamp(payload["exp"]):
                    return last_request.response_body
            except:  # pylint: disable=bare-except
                pass

        auth_response: requests.Response = requests.post(
            self.AUTH_URL,
            json={"username": self.settings.sbat_username, "password": self.settings.sbat_password},
            headers=self.STANDARD_HEADERS,
            timeout=1000,
        )

        add_sbat_request(
            self.db,
            self.settings.sbat_username,
            "authentication",
            url=self.AUTH_URL,
            response=auth_response.status_code,
            response_body=auth_response.text,
        )

        if auth_response.status_code == 200:
            token: str = auth_response.text
            return token
        else:
            raise AuthenticationError("Authentication failed")

    async def check_for_time_slots(self) -> NoReturn:
        token: str = self.authenticate()
        headers: dict[str, str] = {**self.STANDARD_HEADERS, "Authorization": f"Bearer {token}"}

        while True:
            for license_type in self.license_types:
                print(f"Checking for new time slots for license type '{license_type}'...")
                body: dict = {
                    "examCenterId": 1,
                    "licenseType": license_type,
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
                    self.db,
                    self.settings.sbat_username,
                    "check_for_time_slots",
                    self.CHECK_URL,
                    json.dumps(body),
                    response.status_code,
                    response.text if response.status_code != 200 else None,
                )
                print(f"Response status code {response.status_code} for license type '{license_type}', {response.text}")

                if response.status_code == 200:
                    data: dict = response.json()
                    print(data)
                    self.notify_users_and_update_db(data, license_type)

                else:
                    www_authenticate: str | None = response.headers.get("WWW-Authenticate")
                    if response.status_code == 401 and www_authenticate and "The token is expired" in www_authenticate:
                        headers: dict[str, str] = {**self.STANDARD_HEADERS, "Authorization": f"Bearer {self.authenticate()}"}
                        continue
                    else:
                        www_authenticate = response.headers.get("WWW-Authenticate")
                        error_message: str = (
                            f"Unexpected status code {response.status_code}. "
                            f"Headers: {response.headers}. "
                            f"Response Body: {response.text}. "
                            f"WWW-Authenticate Header: {www_authenticate}"
                        )
                        send_telegram_message(
                            f"Got unknown {response.status_code} error: {error_message}",
                            self.settings.telegram_bot_token,
                            self.settings.telegram_chat_id,
                        )

                await asyncio.sleep(self.seconds_inbetween)

    def notify_users_and_update_db(self, time_slots: list[dict], license_type: str) -> None:
        current_time_slots = set()
        notified_time_slots: set = get_notified_time_slots(self.db)
        message: str = ""

        for time_slot in time_slots:
            exam_id: int = time_slot["id"]
            start_time: datetime = datetime.fromisoformat(time_slot["from"])
            end_time: datetime = datetime.fromisoformat(time_slot["till"])
            current_time_slots.add(exam_id)

            if exam_id not in notified_time_slots:

                new_time_slot_messag: str = f"{start_time.date()}  {start_time.time()} - {end_time.time()}\n"
                if new_time_slot_messag not in message:
                    message += new_time_slot_messag

                if get_time_slot_status(self.db, exam_id) == "taken":
                    set_time_slot_status(self.db, exam_id, "notified")
                else:
                    add_time_slot(self.db, time_slot, status="notified")

        if message:
            subject: str = f"New driving exam time_slots available for license type '{license_type}':"
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

        for exam_id in notified_time_slots - current_time_slots:
            set_time_slot_status(self.db, exam_id, "taken")
            set_first_taken_at(self.db, exam_id)
