import json
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from httpx import Response
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorCursor, AsyncIOMotorDatabase

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


@pytest.fixture(scope="module")
def events() -> AsyncIOMotorCollection:
    client: AsyncIOMotorClient = AsyncIOMotorClient(get_settings().database_url)
    return client["rijexamen-meldingen"]["stripe_events"]


@pytest.fixture(scope="function")
def mock_stripe_signature() -> Generator[MagicMock, None, None]:
    with patch("stripe.Webhook.construct_event") as mock:

        def mock_construct_event(payload: bytes, *_) -> dict[str, Any]:
            return json.loads(payload)

        mock.side_effect = mock_construct_event
        yield mock


@pytest.fixture(scope="function")
def mock_create_single_use_invite_link() -> Generator[MagicMock, None, None]:
    with patch("api.webhooks.stripe_handlers.create_single_use_invite_link") as mock:
        mock.side_effect = "test_link"
        yield mock


@pytest.fixture(scope="function")
def mock_send_email() -> Generator[MagicMock, None, None]:
    with patch("api.webhooks.stripe_handlers.send_email") as mock:
        yield mock


# pylint: disable=redefined-outer-name,unused-argument
@pytest.mark.asyncio
async def test_stripe_webhook_for_all_events_in_production_db(
    test_client: TestClient,
    events: AsyncIOMotorCollection,
    mock_stripe_signature: MagicMock,
    mock_create_single_use_invite_link: MagicMock,
    mock_send_email: MagicMock,
) -> None:
    test_mongo_db: AsyncIOMotorDatabase = override_get_mongodb()
    cursor: AsyncIOMotorCursor = events.find({}).limit(10)

    async for event in cursor:
        _: ObjectId = event.pop("_id")
        headers: dict[str, str] = {"stripe-signature": "test-signature"}

        response: Response = test_client.post("/stripe-webhook", json=event, headers=headers)
        mock_stripe_signature.assert_called_once()
        mock_stripe_signature.reset_mock()

        assert response.status_code == 200
        assert response.json() == {"status": "success"}

        if event["type"] not in ("invoice.payment_succeeded", "invoice.payment_failed"):
            mock_send_email.assert_called_once()
            mock_send_email.reset_mock()

        assert await test_mongo_db["stripe_events"].find_one(event) is not None

        data_object: dict = event.get("data").get("object")
        if data_object.get("customer_object"):
            subscriber: dict | None = await test_mongo_db["subscribers"].find_one(
                {
                    "name": data_object.get("customer_details").pop("name"),
                    "email": data_object.get("customer_details").pop("email").lower(),
                    "phone": data_object.get("customer_details").pop("phone"),
                    "stripe_ids": [data_object.get("subscription")],
                    "stripe_customer_id": data_object.get("customer"),
                    "extra_details": data_object.get("customer_details"),
                }
            )
            assert subscriber is not None
        if event["type"] == "checkout.session.completed":
            mock_create_single_use_invite_link.assert_called_once()
            mock_create_single_use_invite_link.reset_mock()
    await test_mongo_db.drop_collection("stripe_events")
    await test_mongo_db.drop_collection("subscribers")
