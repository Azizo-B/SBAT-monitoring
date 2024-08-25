from abc import ABC, abstractmethod

from bson import ObjectId

from ..models.sbat import ExamTimeSlotCreate, ExamTimeSlotRead, MonitorPreferences, SbatRequestCreate, SbatRequestRead
from ..models.subscriber import SubscriberCreate, SubscriberRead


class BaseRepository(ABC):
    @abstractmethod
    async def create_time_slot(self, time_slot: ExamTimeSlotCreate) -> ExamTimeSlotRead:
        """
        Create a new exam time slot in the repository.

        Args:
            time_slot (ExamTimeSlotCreate): The data required to create a time slot.

        Returns:
            ExamTimeSlotRead: The created time slot with its database ID.
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
    async def find_time_slot_by_sbat_exam_id(self, sbat_exam_id: int) -> ExamTimeSlotRead | None:
        """
        Find a time slot in the repository by its SBAT exam ID.

        Args:
            sbat_exam_id (int): The SBAT exam ID.

        Returns:
            ExamTimeSlotRead | None: The corresponding time slot if found, or None if not.
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
    async def mark_time_slot_as_taken(self, sbat_exam_id: int) -> ExamTimeSlotRead | None:
        """
        Mark a specific exam time slot as taken.

        Args:
            sbat_exam_id (int): The SBAT exam ID.

        Returns:
            ExamTimeSlotRead | None: The updated time slot if successful, or None if the update failed.
        """

    @abstractmethod
    async def list_time_slots(self, limit: int = 10) -> list[ExamTimeSlotRead]:
        """
        List exam time slots, with an optional limit on the number of results.

        Args:
            limit (int, optional): The maximum number of time slots to return. Defaults to 10.

        Returns:
            list[ExamTimeSlotRead]: A list of time slots.
        """

    @abstractmethod
    async def create_sbat_request(self, sbat_request: SbatRequestCreate) -> SbatRequestRead:
        """
        Create a new SBAT request in the repository.

        Args:
            sbat_request (SbatRequestCreate): The data required to create the SBAT request.

        Returns:
            SbatRequestRead: The created SBAT request with its database ID.
        """

    @abstractmethod
    async def find_last_sbat_auth_request(self) -> SbatRequestRead | None:
        """
        Find the most recent SBAT authentication request.

        Returns:
            SbatRequestRead | None: The last SBAT authentication request if found, or None if not.
        """

    @abstractmethod
    async def list_requests(self, limit: int = 10) -> list[SbatRequestRead]:
        """
        List SBAT requests, with an optional limit on the number of results.

        Args:
            limit (int, optional): The maximum number of requests to return. Defaults to 10.

        Returns:
            list[SbatRequestRead]: A list of SBAT requests.
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
    async def find_subscriber(self, query: dict) -> SubscriberRead | None:
        """
        Find a subscriber based on a query dictionary.

        Args:
            query (dict): The query dictionary.

        Returns:
            SubscriberRead | None: The subscriber if found, or None if not.
        """

    @abstractmethod
    async def find_subscriber_by_id(self, subscriber_id: str | ObjectId) -> SubscriberRead | None:
        """
        Find a subscriber by their unique ID.

        This method retrieves a subscriber from the database based on their unique identifier.
        The `subscriber_id` parameter can be either a string or an `ObjectId`.

        Args:
            subscriber_id (str | ObjectId): The unique identifier of the subscriber.

        Returns:
            SubscriberRead | None: An instance of `SubscriberRead` if found, otherwise `None`.

        Raises:
            NotImplementedError: If the method is not implemented by the subclass.
        """

    @abstractmethod
    async def find_subscriber_by_email(self, email: str) -> SubscriberRead | None:
        """
        Find a subscriber by their email.

        This method retrieves a subscriber from the database based on their unique email.

        Args:
            email (str): The unique email of the subscriber.

        Returns:
            SubscriberRead | None: An instance of `SubscriberRead` if found, otherwise `None`.

        Raises:
            NotImplementedError: If the method is not implemented by the subclass.
        """

    @abstractmethod
    async def find_subscriber_by_stripe_customer_id(self, stripe_customer_id: str) -> SubscriberRead | None:
        """
        Find a subscriber by their Stripe customer ID.

        This method retrieves a subscriber from the database using their Stripe customer ID.

        Args:
            stripe_customer_id (str): The Stripe customer ID associated with the subscriber.

        Returns:
            SubscriberRead|None: An instance of `SubscriberRead` if found, otherwise `None`.

        Raises:
            NotImplementedError: If the method is not implemented by the subclass.
        """

    @abstractmethod
    async def find_subscriber_by_telegram_link(self, telegram_link: str) -> SubscriberRead | None:
        """
        Find a subscriber by their Telegram link.

        This method retrieves a subscriber from the database using their Telegram invite link.

        Args:
            telegram_link (str): The Telegram link associated with the subscriber.

        Returns:
            SubscriberRead|None: An instance of `SubscriberRead` if found, otherwise `None`.

        Raises:
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
    async def update_subscriber_preferences(self, subscriber_id: str | ObjectId, preferences: MonitorPreferences) -> SubscriberRead | None:
        """
        Update the monitoring preferences of a subscriber.

        Args:
            subscriber_id (str | ObjectId): The ID of the subscriber.
            preferences (MonitorPreferences): The new monitoring preferences.

        Returns:
            SubscriberRead | None: The updated subscriber if successful, or None if the update failed.
        """

    @abstractmethod
    async def update_subscriber_telegram_user(self, subscriber_id: str | ObjectId, telegram_user: dict) -> SubscriberRead | None:
        """
        Update a subscriber's Telegram user information.

        This method updates the Telegram user details for a subscriber identified by their ID.
        The `telegram_user` parameter is a dictionary containing the new Telegram user details.

        Args:
            subscriber_id (str | ObjectId): The unique identifier of the subscriber.
            telegram_user (dict): A dictionary containing the updated Telegram user details.

        Returns:
            SubscriberRead|None: An instance of `SubscriberRead` with updated details if successful, otherwise `None`.

        Raises:
            NotImplementedError: If the method is not implemented by the subclass.
        """

    @abstractmethod
    async def deactivate_subscriber_subscription(self, stripe_customer_id: str) -> SubscriberRead | None:
        """
        Deactivate a subscriber's subscription based on the Stripe customer ID.

        Args:
            stripe_customer_id (str): The Stripe customer ID.

        Returns:
            SubscriberRead | None: The updated subscriber if successful, or None if the update failed.
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
    async def list_subscribers(self, limit: int = 10) -> list[SubscriberRead]:
        """
        List subscribers, with an optional limit on the number of results.

        Args:
            limit (int, optional): The maximum number of subscribers to return. Defaults to 10.

        Returns:
            list[SubscriberRead]: A list of subscribers.
        """

    @abstractmethod
    async def process_checkout_session(self, session: dict, telegram_link: str) -> SubscriberRead:
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
