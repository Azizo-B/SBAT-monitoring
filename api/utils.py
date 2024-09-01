import asyncio
import datetime
import smtplib
from email.message import EmailMessage
from email.utils import formatdate
from typing import Any, Callable, Coroutine, Iterable

import httpx
import jwt
from google.cloud import storage
from jinja2 import Environment, FileSystemLoader, Template


def create_access_token(data: dict, minutes: int, secret_key: str, algorithm: str) -> str:
    to_encode: dict = data.copy()
    expire: datetime.datetime = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)


async def retry_request(request_function: Callable, max_retries: int = 3, max_wait_time: int = 300, min_wait_time: int = 0) -> Any | None:
    """Retry a request function with exponential backoff."""
    for attempt in range(1, max_retries + 1):
        corrected: int | None = None
        try:
            result: Any = await request_function()
            return result
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                corrected = min_wait_time + 60
            if exc.response.status_code in (403, 400):
                return None
        except httpx.RequestError as exc:
            print(f"Attempt {attempt}: An error occurred while requesting {exc.request.url!r}. Error: {exc}")

        wait_time: float = 2**attempt + (0.1 * attempt)
        wait_time = max(wait_time, min_wait_time)
        if corrected:
            wait_time = max(wait_time, corrected)
        wait_time = min(wait_time, max_wait_time)
        print(f"Sleeping for {wait_time} before retry {request_function}")
        await asyncio.sleep(wait_time)
    return None


async def assign_role_to_user(guild_id: str, user_id: str, role_id: str, bot_token: str):
    url: str = f"https://discord.com/api/v10/guilds/{guild_id}/members/{user_id}/roles/{role_id}"
    headers: dict[str, str] = {"Authorization": f"Bot {bot_token}"}

    async def request_function():
        async with httpx.AsyncClient() as client:
            response: httpx.Response = await client.put(url, headers=headers)
            response.raise_for_status()

    return await retry_request(request_function)


async def remove_role_from_user(guild_id: str, user_id: str, role_id: str, bot_token: str):
    url: str = f"https://discord.com/api/v10/guilds/{guild_id}/members/{user_id}/roles/{role_id}"
    headers: dict[str, str] = {"Authorization": f"Bot {bot_token}"}

    async def request_function():
        async with httpx.AsyncClient() as client:
            response: httpx.Response = await client.delete(url, headers=headers)
            response.raise_for_status()

    return await retry_request(request_function)


async def get_role_id_by_name(bot_token: str, guild_id: str, role_name: str) -> str:
    """Asynchronously fetches the role ID by role name from a Discord guild (server)."""
    url: str = f"https://discord.com/api/v10/guilds/{guild_id}/roles"
    headers: dict[str, str] = {"Authorization": f"Bot {bot_token}"}

    async with httpx.AsyncClient() as client:
        response: httpx.Response = await client.get(url, headers=headers)

    if response.status_code == 200:
        roles = response.json()
        for role in roles:
            if role["name"] == role_name:
                return role["id"]


async def get_user_roles_in_guild(guild_id: str, user_id: int, bot_token: str) -> list[str]:
    url: str = f"https://discord.com/api/v10/guilds/{guild_id}/members/{user_id}"
    headers: dict[str, str] = {"Authorization": f"Bot {bot_token}", "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        response: httpx.Response = await client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("roles", [])


async def get_all_roles_in_guild(guild_id: str, bot_token: str) -> list[dict]:
    url: str = f"https://discord.com/api/v10/guilds/{guild_id}/roles"
    headers: dict[str, str] = {"Authorization": f"Bot {bot_token}", "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        response: httpx.Response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()


async def send_discord_message(bot_token: str, channel_id: str, message: str):
    """Asynchronously sends a message to a Discord channel."""
    url: str = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers: dict[str, str] = {"Authorization": f"Bot {bot_token}", "Content-Type": "application/json"}
    payload: dict = {"content": message, "tts": False}

    async with httpx.AsyncClient() as client:
        response: httpx.Response = await client.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        print(f"Failed to send message: {response.status_code} - {response.text}")


async def send_discord_message_with_role_mention(bot_token: str, guild_id: str, channel_id: str, role: str, message: str):
    """sends a message in a specified channel mentioning the role."""
    role_id: str = await get_role_id_by_name(bot_token, guild_id, role)
    message: str = f"<@&{role_id}>\n {message}"
    await send_discord_message(bot_token, channel_id, message)


async def is_user_in_guild(guild_id: str, user_id: str, bot_token: str) -> bool:
    url: str = f"https://discord.com/api/v10/guilds/{guild_id}/members/{user_id}"
    headers: dict[str, str] = {"Authorization": f"Bot {bot_token}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            return True
        elif response.status_code == 404:
            return False


async def send_telegram_message(message: str, bot_token: str, chat_id: str) -> None:
    url: str = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload: dict[str, str] = {"chat_id": chat_id, "text": message}

    async def send_request() -> None:
        async with httpx.AsyncClient() as client:
            response: httpx.Response = await client.post(url, data=payload, timeout=10)
            response.raise_for_status()

    await retry_request(send_request)


async def send_telegram_message_to_all(message: str, bot_token: str, recipient_ids: Iterable):
    tasks: list[Coroutine] = [send_telegram_message(message, bot_token, chat_id) for chat_id in recipient_ids]
    await asyncio.gather(*tasks)


async def create_single_use_invite_link(chat_id: str, bot_token: str, name: str | None = None) -> str | None:
    """Create a single-use invite link for a Telegram chat."""
    url: str = f"https://api.telegram.org/bot{bot_token}/createChatInviteLink"
    payload: dict = {"chat_id": chat_id, "creates_join_request": True}
    if name:
        payload.update({"name": name})

    async def create_request() -> str:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response: httpx.Response = await client.post(url, json=payload)
            response.raise_for_status()
            data: dict = response.json()
            return data["result"]["invite_link"]

    return await retry_request(create_request)


async def revoke_invite_link(chat_id: str, invite_link: str, bot_token: str) -> bool:
    """Revoke a Telegram invite link."""
    url: str = f"https://api.telegram.org/bot{bot_token}/revokeChatInviteLink"
    payload: dict = {"chat_id": chat_id, "invite_link": invite_link}

    async def revoke_request() -> None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response: httpx.Response = await client.post(url, json=payload)
            response.raise_for_status()

    return await retry_request(revoke_request)


async def accept_join_request(chat_id: str, user_id: int, bot_token: str) -> None:
    url: str = f"https://api.telegram.org/bot{bot_token}/approveChatJoinRequest"
    payload: dict = {"chat_id": chat_id, "user_id": user_id}

    async def approve_request() -> None:
        async with httpx.AsyncClient() as client:
            response: httpx.Response = await client.post(url, json=payload)
            response.raise_for_status()

    return await retry_request(approve_request)


async def decline_join_request(chat_id: str, user_id: int, bot_token: str) -> None:
    """Decline a join request for a Telegram chat."""
    url: str = f"https://api.telegram.org/bot{bot_token}/declineChatJoinRequest"
    payload: dict = {"chat_id": chat_id, "user_id": user_id}

    async def decline_request() -> None:
        async with httpx.AsyncClient() as client:
            response: httpx.Response = await client.post(url, json=payload)
            response.raise_for_status()

    return await retry_request(decline_request)


def get_channel_id(bot_token: str) -> None:
    response: httpx.Response = httpx.get(f"https://api.telegram.org/bot{bot_token}/getUpdates")
    if response.status_code == 200:
        data: dict = response.json()
        result_list: list = data.get("result", [])
        for result in result_list:
            print(result)
    else:
        print(f"Failed to get updates. Response: {response.text}")


async def kick_user_from_chat(bot_token: str, chat_id: int, user_id: int):
    url: str = f"https://api.telegram.org/bot{bot_token}/kickChatMember"
    payload: dict[str, int] = {"chat_id": chat_id, "user_id": user_id}
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload)


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
    recipient_list: list[str] | set[str],
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
    if len(recipient_list) == 1:
        msg["To"] = recipient_list.pop()
    else:
        msg["To"] = sender
        msg["Bcc"] = ", ".join(recipient_list)

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
