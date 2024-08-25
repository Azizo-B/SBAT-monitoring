import datetime
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.results import InsertOneResult

from api.dependencies import get_mongodb, get_settings
from api.main import app


def override_get_mongodb() -> AsyncIOMotorDatabase:
    client: AsyncIOMotorClient = AsyncIOMotorClient(get_settings().database_url)
    return client["test-rijexamen-meldingen"]


@pytest.fixture(scope="module")
def test_client() -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_mongodb] = override_get_mongodb
    client: TestClient = TestClient(app)
    yield client
    app.dependency_overrides = {}


@pytest.fixture(scope="function")
def mock_accept_join_request() -> Generator[MagicMock, None, None]:
    with patch("api.webhooks.telegram_handlers.accept_join_request") as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_revoke_invite_link() -> Generator[MagicMock, None, None]:
    with patch("api.webhooks.telegram_handlers.revoke_invite_link") as mock:
        yield mock


@pytest.fixture(scope="function")
def mock_decline_join_request() -> Generator[MagicMock, None, None]:
    with patch("api.webhooks.telegram_handlers.decline_join_request") as mock:
        yield mock


# pylint: disable=redefined-outer-name,unused-argument
@pytest.mark.asyncio
async def test_telegram_webhook_for_chat_join_requests(
    test_client: TestClient,
    mock_accept_join_request: MagicMock,
    mock_revoke_invite_link: MagicMock,
    mock_decline_join_request: MagicMock,
) -> None:
    update: dict = {
        "chat_join_request": {
            "chat": {"id": get_settings().telegram_chat_id},
            "invite_link": {"invite_link": "test_invite_link"},
            "from": {"id": 987654321, "username": "testuser"},
        }
    }

    test_mongo_db: AsyncIOMotorDatabase = override_get_mongodb()
    subscriber_id: InsertOneResult = await test_mongo_db["subscribers"].insert_one(
        {
            "name": "Existing User",
            "email": "existinguser@example.com",
            "hashed_password": "existinghashedpassword123",
            "telegram_user": {},
            "telegram_link": "test_invite_link",
            "role": "user",
            "account_created_on": datetime.datetime.now(datetime.UTC),
        }
    )

    response: Response = test_client.post("/telegram-webhook", json=update)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    mock_accept_join_request.assert_called_once_with(get_settings().telegram_chat_id, 987654321, get_settings().telegram_bot_token)
    mock_revoke_invite_link.assert_called_once_with(get_settings().telegram_chat_id, "test_invite_link", get_settings().telegram_bot_token)
    mock_decline_join_request.assert_not_called()

    updated_subscriber = await test_mongo_db["subscribers"].find_one({"_id": subscriber_id.inserted_id})
    assert updated_subscriber["telegram_user"] == {"id": 987654321, "username": "testuser"}

    await test_mongo_db.drop_collection("subscribers")
    await test_mongo_db.drop_collection("telegram_events")


@pytest.mark.asyncio
async def test_decline_join_request_when_no_subscriber_found(test_client: TestClient, mock_decline_join_request: MagicMock) -> None:
    update: dict = {
        "chat_join_request": {
            "chat": {"id": get_settings().telegram_chat_id},
            "invite_link": {"invite_link": "non_existent_invite_link"},
            "from": {"id": 987654321, "username": "testuser"},
        }
    }

    response: Response = test_client.post("/telegram-webhook", json=update)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    mock_decline_join_request.assert_called_once_with(get_settings().telegram_chat_id, 987654321, get_settings().telegram_bot_token)
    test_mongo_db: AsyncIOMotorDatabase = override_get_mongodb()
    await test_mongo_db.drop_collection("subscribers")
    await test_mongo_db.drop_collection("telegram_events")


@pytest.mark.asyncio
async def test_decline_join_request_when_subscriber_already_has_telegram_user(
    test_client: TestClient, mock_decline_join_request: MagicMock
) -> None:
    update: dict = {
        "chat_join_request": {
            "chat": {"id": get_settings().telegram_chat_id},
            "invite_link": {"invite_link": "test_invite_link"},
            "from": {"id": 987654321, "username": "testuser"},
        }
    }

    test_mongo_db = override_get_mongodb()
    await test_mongo_db["subscribers"].insert_one(
        {
            "name": "Existing User",
            "email": "existinguser@example.com",
            "hashed_password": "existinghashedpassword123",
            "telegram_user": {"id": 123456, "username": "existinguser"},
            "telegram_link": "test_invite_link",
            "role": "user",
            "account_created_on": datetime.datetime.now(datetime.UTC),
        }
    )

    response: Response = test_client.post("/telegram-webhook", json=update)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    mock_decline_join_request.assert_called_once_with(get_settings().telegram_chat_id, 987654321, get_settings().telegram_bot_token)
    await test_mongo_db.drop_collection("subscribers")
    await test_mongo_db.drop_collection("telegram_events")


@pytest.mark.asyncio
async def test_ignore_chat_join_request_for_different_chat(
    test_client: TestClient, mock_accept_join_request: MagicMock, mock_decline_join_request: MagicMock
) -> None:
    update: dict = {
        "chat_join_request": {
            "chat": {"id": "different_chat_id"},
            "invite_link": {"invite_link": "test_invite_link"},
            "from": {"id": 987654321, "username": "testuser"},
        }
    }

    response: Response = test_client.post("/telegram-webhook", json=update)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    mock_accept_join_request.assert_not_called()
    mock_decline_join_request.assert_not_called()
    test_mongo_db: AsyncIOMotorDatabase = override_get_mongodb()
    await test_mongo_db.drop_collection("subscribers")
    await test_mongo_db.drop_collection("telegram_events")


@pytest.mark.asyncio
async def test_ignore_request_with_no_chat_join_request(
    test_client: TestClient, mock_accept_join_request: MagicMock, mock_decline_join_request: MagicMock
) -> None:
    update: dict = {
        "message": {
            "chat": {"id": get_settings().telegram_chat_id},
            "text": "test",
            "from": {"id": 987654321, "username": "testuser"},
        }
    }

    response: Response = test_client.post("/telegram-webhook", json=update)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    mock_accept_join_request.assert_not_called()
    mock_decline_join_request.assert_not_called()
    test_mongo_db: AsyncIOMotorDatabase = override_get_mongodb()
    await test_mongo_db.drop_collection("subscribers")
    await test_mongo_db.drop_collection("telegram_events")
