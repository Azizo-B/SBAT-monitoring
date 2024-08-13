import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from google.cloud import storage


def send_telegram_message(message: str, bot_token: str, chat_id: str) -> None:
    url: str = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload: dict[str, str] = {"chat_id": chat_id, "text": message}
    response: requests.Response = requests.post(url, data=payload, timeout=1000)
    print(response.json())


def send_email_to(subject: str, message: str, recipient_list: list[str], sender: str, password: str, smpt_server: str, smtp_port) -> None:
    """Send an email to the provided recipients."""
    if not recipient_list:
        print("No recipients provided")
        return

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["Subject"] = subject
    msg.attach(MIMEText(message, "plain"))

    try:
        with smtplib.SMTP(smpt_server, smtp_port) as server:
            server.starttls()
            server.login(sender, password)
            for recipient in recipient_list:
                msg["To"] = recipient
                server.sendmail(sender, recipient, msg.as_string())
                print(f"Email sent to {recipient}")
    except Exception as e:  # pylint: disable=broad-except
        print(f"Failed to send email: {e}")


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
