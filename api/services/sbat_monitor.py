import asyncio
from datetime import datetime, timedelta
from multiprocessing import AuthenticationError
from typing import Literal, NoReturn

import httpx
import jwt
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..db import mongoDB
from ..dependencies import Settings
from ..models import EXAM_CENTER_MAP, MonitorConfiguration, MonitorStatus, SbatRequestRead
from ..utils import send_email, send_telegram_message, send_telegram_message_to_all


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

    def __init__(self, db: AsyncIOMotorDatabase, settings: Settings, config: MonitorConfiguration) -> None:
        self.db: AsyncIOMotorDatabase = db
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

    async def authenticate(self) -> str:
        last_request: SbatRequestRead | None = await mongoDB.get_last_sbat_auth_request(self.db)
        if last_request:
            try:
                payload: dict = jwt.decode(last_request.response_body.get("token"), options={"verify_signature": False})
                if datetime.now() < datetime.fromtimestamp(payload["exp"]):
                    return last_request.response_body.get("token")
            except (jwt.DecodeError, jwt.InvalidTokenError, jwt.ExpiredSignatureError):
                pass

        async with httpx.AsyncClient() as client:
            auth_response: httpx.Response = await client.post(
                self.AUTH_URL,
                json={"username": self.settings.sbat_username, "password": self.settings.sbat_password},
                headers=self.STANDARD_HEADERS,
                timeout=60,
            )

        await mongoDB.add_sbat_request(
            db=self.db,
            email_used=self.settings.sbat_username,
            request_type="authentication",
            url=self.AUTH_URL,
            response=auth_response.status_code,
            response_body={"token": auth_response.text},
        )

        if auth_response.status_code == 200:
            token: str = auth_response.text
            return token
        else:
            raise AuthenticationError("Authentication failed")

    async def check_for_time_slots(self) -> NoReturn:
        token: str = await self.authenticate()
        headers: dict[str, str] = {**self.STANDARD_HEADERS, "Authorization": f"Bearer {token}"}

        while True:
            for license_type in self.license_types:
                for exam_center_id in self.exam_center_ids:
                    exam_center_name: str = EXAM_CENTER_MAP[exam_center_id]
                    response: httpx.Response = await self._perform_check(headers, license_type, exam_center_id, exam_center_name)
                    print(
                        f"Response status code {response.status_code}",
                        f"for license type '{license_type}' in '{exam_center_name}', {response.text}",
                    )

                    # possible exp of token
                    if self._is_exp_error(response):
                        headers: dict[str, str] = {**self.STANDARD_HEADERS, "Authorization": f"Bearer {await self.authenticate()}"}
                        continue

                    await self._handle_response(response, license_type, exam_center_id)
                    await asyncio.sleep(self.seconds_inbetween)

    async def _perform_check(
        self, headers: dict[str, str], license_type: str, exam_center_id: int, exam_center_name: str
    ) -> httpx.Response:
        print(f"Checking '{exam_center_name}' for new time slots for license type '{license_type}'...")
        async with httpx.AsyncClient() as client:
            body: dict = {
                "examCenterId": exam_center_id,
                "licenseType": license_type,
                "examType": "E2",
                "startDate": datetime.combine(datetime.now().date(), datetime.min.time()).isoformat(),
            }
            response: httpx.Response = await client.post(
                self.CHECK_URL,
                headers=headers,
                json=body,
                timeout=60,
            )

        await mongoDB.add_sbat_request(
            db=self.db,
            email_used=self.settings.sbat_username,
            request_type="check_for_time_slots",
            url=self.CHECK_URL,
            request_body=body,
            response=response.status_code,
            response_body=response.text if response.status_code != 200 else None,
        )

        return response

    def _is_exp_error(self, response: httpx.Response) -> bool:
        www_authenticate: str | None = response.headers.get("WWW-Authenticate")
        return response.status_code == 401 and www_authenticate and "The token is expired" in www_authenticate

    async def _handle_response(self, response: httpx.Response, license_type: str, exam_center_id: int) -> None:
        exam_center_name: str = EXAM_CENTER_MAP[exam_center_id]
        if response.status_code == 200:
            data: dict = response.json()
            print(data)
            await self.notify_users_and_update_db(data, exam_center_id, exam_center_name, license_type)

        else:
            www_authenticate: str | None = response.headers.get("WWW-Authenticate")
            error_message: str = (
                f"Unexpected status code {response.status_code}. "
                f"Headers: {response.headers}. "
                f"Response Body: {response.text}. "
                f"WWW-Authenticate Header: {www_authenticate}"
            )
            await send_telegram_message(
                f"Got unknown {response.status_code} error: {error_message}",
                self.settings.telegram_bot_token,
                self.settings.telegram_chat_id,
            )

    async def notify_users_and_update_db(
        self, time_slots: list[dict], exam_center_id: int, exam_center_name: str, license_type: str
    ) -> None:
        current_time_slots = set()
        notified_time_slots: set[int] = await mongoDB.get_notified_time_slots(self.db, exam_center_id, license_type)
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

                if await mongoDB.get_time_slot_status(self.db, exam_id) == "taken":
                    await mongoDB.set_time_slot_status(self.db, exam_id, "notified")
                else:
                    await mongoDB.add_time_slot(self.db, time_slot, status="notified")

        if message:
            subject: str = f"New driving exam time slots available for license type '{license_type}' at exam center '{exam_center_name}':"
            message: str = subject + "\nLink: https://rijbewijs.sbat.be/praktijk/examen/Login \n" + message
            email_recipients: list[str] = await mongoDB.get_all_subscribed_mails(self.db, exam_center_id, license_type)
            telegram_recipients: list[str] = await mongoDB.get_all_telegram_user_ids(self.db, exam_center_id, license_type)
            send_email(
                subject,
                email_recipients,
                self.settings.sender_email,
                self.settings.sender_password,
                self.settings.smtp_server,
                self.settings.smtp_port,
                message=message,
            )
            await send_telegram_message_to_all(message, self.settings.telegram_bot_token, telegram_recipients)

        for exam_id in notified_time_slots - current_time_slots:
            await mongoDB.set_time_slot_status(self.db, exam_id, "taken")
            await mongoDB.set_first_taken_at(self.db, exam_id)
