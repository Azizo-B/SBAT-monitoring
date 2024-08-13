import asyncio
import json
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from multiprocessing import AuthenticationError
from typing import NoReturn

import requests
from google.cloud import storage
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

DATABASE_FILE: str | None = os.getenv("DATABASE_FILE")
BUCKET_NAME: str | None = os.getenv("BUCKET_NAME")
BLOB_NAME: str | None = os.getenv("BLOB_NAME")

TELEGRAM_BOT_TOKEN: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID: str | None = os.getenv("CHAT_ID")
SENDER_EMAIL: str | None = os.getenv("EMAIL_SENDER")
SENDER_PASSWORD: str | None = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER: str | None = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
AUTH_URL = "https://api.rijbewijs.sbat.be/praktijk/api/user/authenticate"
CHECK_URL = "https://api.rijbewijs.sbat.be/praktijk/api/exam/available"
LICENSETYPE = "B"
TIME_BETWEEN_REQUESTS: int = int(os.getenv("TIME_BETWEEN_REQUESTS", "600"))

STANDARD_HEADERS: dict[str, str] = {
    "Cache-Control": "no-cache",
    "Content-Type": "application/json",
    "Accept": "*/*",
    "Connection": "keep-alive",
    "User-Agent": "PostmanRuntime/7.39.1",
    "Accept-Encoding": "gzip, deflate, br",
}


def reauthenticate(db: Session) -> str:
    auth_response: requests.Response = requests.post(
        AUTH_URL,
        json={"username": os.getenv("SBAT_USERNAME"), "password": os.getenv("SBAT_PASSWORD")},
        headers=STANDARD_HEADERS,
        timeout=1000,
    )

    add_sbat_request(db, os.getenv("SBAT_USERNAME"), "authentication", url=AUTH_URL, response=auth_response.status_code)

    if auth_response.status_code == 200:
        token: str = auth_response.text
        return token
    else:
        raise AuthenticationError("Authentication failed")


async def check_for_dates(db: Session, license_type: str = "B") -> NoReturn:
    counter = 0
    token: str = reauthenticate(db)
    headers: dict[str, str] = {**STANDARD_HEADERS, "Authorization": f"Bearer {token}"}

    while True:
        print("Checking for new dates...")
        body: dict = {
            "examCenterId": 1,
            "licenseType": license_type,
            "examType": "E2",
            "startDate": datetime.combine(datetime.now().date(), datetime.min.time()).isoformat(),
        }
        response: requests.Response = requests.post(
            CHECK_URL,
            headers=headers,
            json=body,
            timeout=1000,
        )

        counter += 1
        print(f"Request {counter} made")
        add_sbat_request(db, os.getenv("SBAT_USERNAME"), "check_for_dates", CHECK_URL, json.dumps(body), response.status_code)
        print(f"Response status code {response.status_code}")

        if response.status_code == 200:
            data: dict = response.json()
            print(data)
            notify_users_and_update_db(db, data, license_type)

        elif response.status_code == 401:
            headers: dict[str, str] = {**STANDARD_HEADERS, "Authorization": f"Bearer {reauthenticate(db)}"}
            continue

        await asyncio.sleep(TIME_BETWEEN_REQUESTS)


def notify_users_and_update_db(db: Session, dates: list[dict], license_type: str = "B") -> None:
    current_dates = set()
    notified_dates: set = get_notified_dates(db)
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

            if get_date_status(db, exam_id) == "taken":
                set_date_status(db, exam_id, "notified")
            else:
                add_date(db, date, status="notified")

    if message:
        subject: str = f"New driving exam dates available for license type '{license_type}':"
        message: str = subject + "\n\n" + message
        send_email_to_subscribers(subject, message, get_all_subscribers(db))
        send_telegram_message(message)

    for exam_id in notified_dates - current_dates:
        set_date_status(db, exam_id, "taken")
        set_first_taken_at(db, exam_id)


def send_telegram_message(message: str) -> None:
    url: str = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload: dict[str, str] = {"chat_id": CHAT_ID, "text": message}
    response: requests.Response = requests.post(url, data=payload, timeout=1000)
    print(response.json())


def send_email_to_subscribers(subject: str, message: str, recipient_list: list[str]) -> None:
    if not recipient_list:
        print("No recipients provided")
        return

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(message, "plain"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            for recipient in recipient_list:
                msg["To"] = recipient
                server.sendmail(SENDER_EMAIL, recipient, msg.as_string())
                print(f"Email sent to {recipient}")
    except Exception as e:  # pylint: disable=broad-except
        print(f"Failed to send email: {e}")


key_path: str | None = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")


def download_db() -> None:
    """Download the SQLite file from GCS to the local filesystem."""
    client = storage.Client()
    bucket: storage.Bucket = client.bucket(BUCKET_NAME)
    blob: storage.Blob = bucket.blob(BLOB_NAME)
    blob.download_to_filename(DATABASE_FILE)
    print(f"Downloaded database from {BLOB_NAME} to {DATABASE_FILE}")


def upload_db() -> None:
    """Upload the SQLite file from the local filesystem to GCS."""
    client = storage.Client()
    bucket: storage.Bucket = client.bucket(BUCKET_NAME)
    blob: storage.Blob = bucket.blob(BLOB_NAME)
    blob.upload_from_filename(DATABASE_FILE)
    print(f"Uploaded database from {DATABASE_FILE} to {BLOB_NAME}")
