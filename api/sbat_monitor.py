import asyncio
import json
from datetime import datetime, timedelta
from multiprocessing import AuthenticationError
from typing import Literal, NoReturn

import jwt
from requests import Response, post
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
from .models import EXAM_CENTER_MAP, MonitorConfiguration, MonitorStatus
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

    def __init__(self, db: Session, settings: Settings, config: MonitorConfiguration) -> None:
        self.db: Session = db
        self.settings: Settings = settings

        # Initialize with default values to ensure consistency
        self.license_types: list[Literal["B", "AM"]] = ["B"]
        self.exam_center_ids: list[int] = [1]
        self.seconds_inbetween: int = 300

        self.config = config

        self.task: asyncio.Task | None = None
        self.total_time_running: timedelta = timedelta()
        self.first_started_at: datetime | None = None
        self.last_started_at: datetime | None = None
        self.last_stopped_at: datetime | None = None

    @property
    def config(self) -> MonitorConfiguration:
        return self._config

    @config.setter
    def config(self, new_config) -> None:
        if not isinstance(new_config, MonitorConfiguration):
            raise TypeError("Expected new_config to be an instance of MonitorConfiguration")

        self._config: MonitorConfiguration = new_config
        self.license_types: list[Literal["B", "AM"]] = new_config.license_types
        self.exam_center_ids: list[int] = new_config.exam_center_ids
        self.seconds_inbetween: int = new_config.seconds_inbetween

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
            exam_centers=[EXAM_CENTER_MAP[c_id] for c_id in self.exam_center_ids],
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

        auth_response: Response = post(
            self.AUTH_URL,
            json={"username": self.settings.sbat_username, "password": self.settings.sbat_password},
            headers=self.STANDARD_HEADERS,
            timeout=60,
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
                for exam_center_id in self.exam_center_ids:
                    exam_center_name: str = EXAM_CENTER_MAP[exam_center_id]
                    response: Response = self._perform_check(headers, license_type, exam_center_id, exam_center_name)
                    print(
                        f"Response status code {response.status_code}",
                        f"for license type '{license_type}' in '{exam_center_name}', {response.text}",
                    )

                    # possible exp of token
                    if self._is_exp_error(response):
                        headers: dict[str, str] = {**self.STANDARD_HEADERS, "Authorization": f"Bearer {self.authenticate()}"}
                        continue

                    self._handle_response(response, license_type, exam_center_name)
                    await asyncio.sleep(self.seconds_inbetween)

    def _perform_check(self, headers: dict[str, str], license_type: str, exam_center_id: int, exam_center_name: str) -> Response:
        print(f"Checking '{exam_center_name}' for new time slots for license type '{license_type}'...")
        body: dict = {
            "examCenterId": exam_center_id,
            "licenseType": license_type,
            "examType": "E2",
            "startDate": datetime.combine(datetime.now().date(), datetime.min.time()).isoformat(),
        }
        response: Response = post(
            self.CHECK_URL,
            headers=headers,
            json=body,
            timeout=60,
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
        return response

    def _is_exp_error(self, response: Response) -> bool:
        www_authenticate: str | None = response.headers.get("WWW-Authenticate")
        return response.status_code == 401 and www_authenticate and "The token is expired" in www_authenticate

    def _handle_response(self, response: Response, license_type: str, exam_center_name: str) -> None:
        if response.status_code == 200:
            data: dict = response.json()
            print(data)
            self.notify_users_and_update_db(data, exam_center_name, license_type)

        else:
            www_authenticate: str | None = response.headers.get("WWW-Authenticate")
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

    def notify_users_and_update_db(self, time_slots: list[dict], exam_center_name: str, license_type: str) -> None:
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
            subject: str = f"New driving exam time slots available for license type '{license_type}' at exam center '{exam_center_name}':"
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
