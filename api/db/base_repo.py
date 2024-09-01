from abc import ABC, abstractmethod
from typing import Type

from pydantic import BaseModel

from ..models.sbat import ExamTimeSlotRead, SbatRequestRead
from ..models.subscriber import SubscriberCreate, SubscriberRead


class BaseRepository(ABC):

    @abstractmethod
    async def create(self, table_or_collection: str, data_model: BaseModel, pydantic_return_model: Type[BaseModel]) -> BaseModel:
        """
        Create a new document or row in the repository.

        Args:
            table_or_collection (str): The name of the collection or table.
            data_model (BaseModel): The Pydantic model instance containing the data to insert.
            pydantic_return_model (Type[BaseModel]): The Pydantic model class to use for deserializing the result.

        Returns:
            BaseModel: The created document or row as a Pydantic model.
        """

    @abstractmethod
    async def find(self, table_or_collection: str, query_dict: dict, pydantic_return_model: Type[BaseModel]) -> list[BaseModel]:
        """
        Finds documents or rows in a collection or table based on the provided query dictionary
        returns the results as a list of Pydantic models.

        Args:
            table_or_collection (str): The name of the collection or table.
            query_dict (dict): A dictionary specifying the query criteria.('field':'value_to_match')
            pydantic_return_model (BaseModel): The Pydantic model class to use for deserializing the results.

        Returns:
            list[BaseModel]: A list of Pydantic model instances representing the query results.
        """

    @abstractmethod
    async def find_one(self, table_or_collection: str, query_dict: dict, pydantic_return_model: BaseModel) -> BaseModel | None:
        """
        Finds a document or row in a collection or table based on the provided query dictionary
        returns the results as a Pydantic models if found else None.

        Args:
            table_or_collection (str): The name of the collection or table.
            query_dict (dict): A dictionary specifying the query criteria.('field':'value_to_match')
            pydantic_return_model (BaseModel): The Pydantic model class to use for deserializing the results.

        Returns:
            BaseModel | None: Pydantic model instances representing the result or None if no matching results were found.
        """

    @abstractmethod
    async def update_one(
        self, table_or_collection: str, query_dict: dict, update_dict: dict, pydantic_return_model: Type[BaseModel]
    ) -> BaseModel | None:
        """
        Update an existing document or row in the repository.

        Args:
            table_or_collection (str): The name of the collection or table.
            query_dict (dict): A dictionary specifying the query criteria. ('field': 'value_to_match')
            update_dict (dict): dict containing the data to update.
            pydantic_return_model (Type[BaseModel]): The Pydantic model class to use for deserializing the result.

        Returns:
            BaseModel | None: The updated document or row as a Pydantic model, or None if no matching document was found.
        """

    @abstractmethod
    async def find_notified_time_slot_ids(self, exam_center_id: int, license_type: str) -> set[int]:
        """
        Retrieve a set of time slot IDs that have been marked as 'notified' for a specific exam center and license type.

        Args:
            exam_center_id (int): The ID of the exam center.
            license_type (str): The type of license related to the exam.

        Returns:
            set[int]: A set of SBAT exam IDs that have been notified.
        """

    @abstractmethod
    async def update_time_slot_status(self, sbat_exam_id: int, status: str) -> ExamTimeSlotRead | None:
        """
        Update the status of a specific exam time slot.

        Args:
            exam_id (int): The SBAT exam ID.
            status (str): The new status to set.

        Returns:
            ExamTimeSlotRead | None: The updated time slot if successful, or None if the update failed.
        """

    @abstractmethod
    async def find_last_sbat_auth_request(self) -> SbatRequestRead | None:
        """
        Find the most recent SBAT authentication request.

        Returns:
            SbatRequestRead | None: The last SBAT authentication request if found, or None if not.
        """

    @abstractmethod
    async def create_subscriber(self, subscriber: SubscriberCreate) -> SubscriberRead:
        """
        Create a new subscriber in the repository.

        Args:
            subscriber (SubscriberCreate): The data required to create the subscriber.

        Returns:
            SubscriberRead: The created subscriber with its database ID.

        Raises:
            Exception: If the subscriber is already in the repository
            NotImplementedError: If the method is not implemented by the subclass.
        """

    @abstractmethod
    async def find_subscriber_by_telegram_user_id(self, telegram_user_id: int) -> SubscriberRead | None:
        """
        Find a subscriber by their Telegram user ID.

        This method retrieves a subscriber from the database using their Telegram user ID.

        Args:
            telegram_user_id (int): The Telegram user ID associated with the subscriber.

        Returns:
            SubscriberRead | None: An instance of `SubscriberRead` if found, otherwise `None`.

        Raises:
            NotImplementedError: If the method is not implemented by the subclass.
        """

    @abstractmethod
    async def find_subscriber_by_discord_user_id(self, discord_user_id: int) -> SubscriberRead | None:
        """
        Find a subscriber by their discord user ID.

        This method retrieves a subscriber from the database using their discord user ID.

        Args:
            discord_user_id (int): The discord user ID associated with the subscriber.

        Returns:
            SubscriberRead | None: An instance of `SubscriberRead` if found, otherwise `None`.

        Raises:
            NotImplementedError: If the method is not implemented by the subclass.
        """

    @abstractmethod
    async def find_all_subscribed_emails(self, exam_center_id: int, license_type: str) -> set[str]:
        """
        Find all emails of subscribers who are monitoring a specific exam center and license type.

        Args:
            exam_center_id (int): The ID of the exam center.
            license_type (str): The license type.

        Returns:
            set[str]: A list of subscribed email addresses.
        """

    @abstractmethod
    async def find_all_subscribed_telegram_ids(self, exam_center_id: int, license_type: str) -> set[int]:
        """
        Find all Telegram user IDs of subscribers who are monitoring a specific exam center and license type.

        Args:
            exam_center_id (int): The ID of the exam center.
            license_type (str): The license type.

        Returns:
            set[int]: A list of subscribed Telegram user IDs.
        """

    @abstractmethod
    async def verify_subscriber_credentials(self, username: str, password: str) -> SubscriberRead | None:
        """
        Verify the credentials of a subscriber.

        Args:
            username (str): The subscriber's username (email).
            password (str): The subscriber's password.

        Returns:
            SubscriberRead | None: The subscriber's data if credentials are valid, or None if invalid.
        """

    @abstractmethod
    async def activate_subscriber_subscription(self, stripe_customer_id: str, amount_paid: int) -> SubscriberRead | None:
        """
        Activate a subscriber's subscription and increment the total amount paid.

        Args:
            stripe_customer_id (str): The Stripe customer ID.
            amount_paid (int): The amount paid to activate the subscription.

        Returns:
            SubscriberRead | None: The updated subscriber if successful, or None if the update failed.
        """

    @abstractmethod
    async def process_checkout_session(self, session: dict) -> SubscriberRead:
        """
        Process a Stripe checkout session and update the corresponding subscriber's information.

        Args:
            session (dict): The Stripe session data.
            telegram_link (str): A link to the subscriber's Telegram account.

        Returns:
            SubscriberRead: The updated subscriber after processing the session.
        """

    @abstractmethod
    async def create_stripe_event(self, stripe_event: dict) -> None:
        """
        Process and store a Stripe event.

        This method handles incoming Stripe events (e.g., webhook notifications) and updates
        the database accordingly. The `stripe_event` parameter contains the event
        sent by Stripe.

        Args:
            stripe_event (dict): The Stripe event.

        Raises:
            NotImplementedError: If the method is not implemented by the subclass.
        """

    @abstractmethod
    async def create_telegram_event(self, telegram_event: dict) -> None:
        """
        Process and store a Telegram event.

        This method handles incoming Telegram events (e.g., messages or updates) and updates
        the database accordingly. The `telegram_event` parameter contains the event
        sent by Telegram.

        Args:
            telegram_event (dict): The Telegram event.

        Raises:
            NotImplementedError: If the method is not implemented by the subclass.
        """

    @abstractmethod
    async def create_discord_event(self, discord_event: dict) -> None:
        """
        Process and store a discord event.

        This method handles incoming discord events (e.g., messages or updates) and updates
        the database accordingly. The `discord_event` parameter contains the event
        sent by discord.

        Args:
            discord_event (dict): The discord event.

        Raises:
            NotImplementedError: If the method is not implemented by the subclass.
        """
