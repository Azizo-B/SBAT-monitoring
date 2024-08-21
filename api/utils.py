import smtplib
from email.message import EmailMessage
from email.utils import formatdate

import httpx
from google.cloud import storage
from jinja2 import Environment, FileSystemLoader, Template


async def send_telegram_message(message: str, bot_token: str, chat_id: str) -> None:
    url: str = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload: dict[str, str] = {"chat_id": chat_id, "text": message}
    async with httpx.AsyncClient() as client:
        response: httpx.Response = await client.post(url, data=payload, timeout=10)
    print(f"Message sent to telegram chat: {chat_id} \nResponse: {response.status_code}")


def get_channel_id(bot_token: str) -> None:
    response: httpx.Response = httpx.get(f"https://api.telegram.org/bot{bot_token}/getUpdates")
    if response.status_code == 200:
        data: dict = response.json()
        result_list: list = data.get("result", [])
        for result in result_list:
            print(result)
    else:
        print(f"Failed to get updates. Response: {response.text}")


def download_file_from_gcs(bucket_name: str, blob_name: str, destination_filename: str) -> None:
    """Download a file from GCS to the local filesystem."""
    client = storage.Client()
    bucket: storage.Bucket = client.bucket(bucket_name)
    blob: storage.Blob = bucket.blob(blob_name)
    blob.download_to_filename(destination_filename)
    print(f"Downloaded database from {blob_name} to {destination_filename}")


def upload_file_to_gcs(bucket_name: str, blob_name: str, source_filename: str) -> None:
    """Upload a file from the local filesystem to GCS."""
    client = storage.Client()
    bucket: storage.Bucket = client.bucket(bucket_name)
    blob: storage.Blob = bucket.blob(blob_name)
    blob.upload_from_filename(source_filename)
    print(f"Uploaded database from {source_filename} to {blob_name}")


def render_template(template_name: str, **kwargs) -> str:
    """Render a Jinja2 template with given variables."""
    env = Environment(loader=FileSystemLoader("templates"))
    template: Template = env.get_template(template_name)
    return template.render(**kwargs)


def send_email(
    subject: str,
    recipient_list: list[str],
    sender: str,
    password: str,
    smtp_server: str,
    smtp_port: int,
    attachments: list[str] | None = None,
    is_html: bool = False,
    message: str | None = None,
    html_template: str | None = None,
    **kwargs,
) -> None:
    """Send an email to the provided recipients."""
    if not recipient_list:
        print("No recipients provided")
        return
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(recipient_list)
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)

    if is_html and html_template:
        template: str = render_template(html_template, **kwargs)
        msg.add_alternative(template, subtype="html")
    else:
        msg.set_content(message)

    if attachments:
        print("cannot add attachment is not implemented")

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender, password)
            server.send_message(msg)
            print(f"Email sent to {len(recipient_list)} recipients")
    except Exception as e:  # pylint: disable=broad-except
        print(f"Failed to send email: {e}")
