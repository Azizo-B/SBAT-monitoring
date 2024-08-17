# SBAT Monitoring System

## Overview

The **SBAT Monitoring System** is a Python API designed to monitor and notify users of available driving exam time slots from the SBAT API. The system periodically checks for new available time slots and sends notifications via email and Telegram when new slots open up. It also tracks the total runtime and provides status updates on the monitoring process.

## Table of Contents

- [Design Choices](#design-choices)
- [Getting Started](#getting-started)
- [API Endpoints](#api-endpoints)
- [Configuration Options](#configuration-options)
- [Possible Flow of the API](#possible-flow-of-the-api)

## Design Choices

- ### Distributed Client-Side Requests: Considerations and Ethical Concerns

  #### Potential Idea:

  At one point, I considered an approach where each user's browser would make API requests directly to the SBAT API. The thought was that by distributing the requests across different IPs and devices, it would be possible to get updates more frequently and allow users to see changes faster.

  #### Why I Didn’t Go This Route:

  Ultimately, I decided against this. While it might have worked technically, it raised ethical concerns. Bypassing rate limits through distributed requests could violate the SBAT API's terms of service. It’s important to respect the rules set by API providers to ensure everyone has fair access to the service.

  So, instead of pushing the limits, I stuck to a more straightforward approach that stays within the guidelines and keeps things fair for everyone.

- ### SQLite Database with Google Cloud Storage (GCS)

  The application uses SQLite as its local database for simplicity and cost-effectiveness. SQLite is a serverless, self-contained database engine, which means it does not require a separate server process. By storing the SQLite database file in Google Cloud Storage (GCS), the application ensures data persistence and backup while keeping costs low. This approach avoids the expenses associated with running a cloud SQL instance continuously, making it a more economical solution for 24/7 operation.

- ### Singleton Pattern for SbatMonitor

  The `SbatMonitor` class is designed as a singleton. This design choice ensures that only one instance of the monitor is created and shared across the application. This pattern prevents multiple instances from running concurrently, which could lead to conflicting operations. It also simplifies the management and tracking of the monitoring task's state, providing a consistent and controlled environment.

- ### BaseSettings Configuration

  The application uses a `BaseSettings` class for configuration management. This class centralizes the configuration settings, such as SBAT API credentials and notification preferences, in one place. By using `BaseSettings`, the configuration can be easily managed and updated without altering the core application logic. This design choice enhances maintainability and flexibility, making it easier to adapt to changes in configuration requirements.

- ### Persistent Database Session

  The `SbatMonitor` class maintains a persistent database session to ensure that database operations are efficient and reliable. Keeping a persistent session open reduces the overhead of repeatedly opening and closing connections, which can be costly in terms of performance. This approach is particularly useful for applications that need to perform frequent database operations, as it helps to minimize latency and maintain a consistent connection state.

## Getting Started

This section explains how to set up the SBAT Monitoring System on your local machine.

**Prerequisites:**

- A SBAT account is required
- A Google Cloud Platform account (optional, for database storage)

**Steps:**

1. **Clone the Repository:**

2. **Create a Virtual Environment:**

   It's recommended to create a virtual environment to manage dependencies:

   ```bash
   python -m venv .venv
   ```

   Activate the virtual environment:

   - On Windows:

     ```
     .venv\Scripts\activate
     ```

   - On macOS/Linux:

     ```
     source .venv/bin/activate
     ```

3. **Install Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Create a .env File:**

   Create a file named `.env` in the root directory of the project and add the following environment variables, replacing the placeholders with your actual values:

   ```bash
   # database Configuration (Required)
   DATABASE_URL=database_url

   # SBAT API Credentials (Required)
   SBAT_USERNAME=your_sbat_username
   SBAT_PASSWORD=your_sbat_passwords

   # Telegram Notification Settings (Optional)
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   TELEGRAM_CHAT_ID=your_telegram_chat_id

   # Email Notification Settings (Optional)
   SENDER_EMAIL=email_used_to_send_notifications
   SENDER_PASSWORD=email_password
   SMTP_SERVER=smtp.gmail.com # Example for Gmail - adjust if needed
   SMTP_PORT=587 # Typical port for secure email

   # Google Cloud Storage Settings (Optional, for database storage)
   GOOGLE_APPLICATION_CREDENTIALS=path/to/your/google_application_credentials.json
   DATABASE_FILE=path/to/your/local/database.db
   BUCKET_NAME=your_gcs_bucket_name
   BLOB_NAME=your_desired_gcs_filename.db
   ```

   **Note:**

   - If you don't plan on using Google Cloud Storage for database persistence, you can comment out or remove the `GOOGLE_APPLICATION_CREDENTIALS`, `DATABASE_FILE`, `BUCKET_NAME` and `BLOB_NAME` variables. The system will automatically exclude operations related to Google Cloud Storage.

5. **Run the Application:**

   ```bash
   uvicorn main:app --reload
   ```

6. **Access the API Documentation:**

   Once the application is running, you can access the API documentation at:
   http://127.0.0.1:8000/docs

## API Endpoints

### Monitoring Endpoints

- **`POST /startup`**

  Starts the monitoring process. Allows updating the monitoring configuration (e.g., `seconds_inbetween` and `license_types`) before starting.

- **`POST /monitor-config`**

  Updates the monitoring configuration and returns the current status of the monitoring task.

- **`GET /monitor-status`**

  Retrieves the current status of the monitoring task.

- **`GET /shutdown`**

  Stops the monitoring process.

### Notification Endpoints

- **`POST /subscribe`**

  Adds an email to the list of subscribers.

- **`POST /unsubscribe`**

  Removes an email from the list of subscribers.

### DB Queries Endpoints

- **`GET /request`**

  Retrieves all SBAT request records from the database.

- **`GET /exam-time-slots`**

  Retrieves all exam time slot records from the database.

## Configuration Options

The `MonitorConfiguration` class defines the configuration settings for the SBAT Monitoring System. Below are the available configuration options, their default values, and descriptions:

- **`license_types`**: `List[Literal["B", "AM"]]`

  - **Description**: A list of driving license types to monitor. Valid values are `"B"` for car licenses and `"AM"` for motorcycle licenses. The license types are based on the codes used by the SBAT API, you can add their respective letters to this list. For example, if the SBAT API introduces a new license type `"C"`, you can include `"C"` in this list to monitor that type as well.
  - **Default Value**: `["B"]`

- **`exam_center_ids`**: `List[int]`

  - **Description**: A list of exam center IDs to check for available time slots. These IDs correspond to specific locations. If the SBAT API adds new exam centers, you can include their respective IDs in this dict found in `api/models.py`

    `{1: "Sint-Denijs-Westrem", 7: "Brakel", 8: "Eeklo", 9: "Erembodegem", 10: "Sint-Niklaas"}`

  - **Default Value**: `[1]` (corresponding to `"Sint-Denijs-Westrem"`)

- **`seconds_inbetween`**: `PositiveInt`
  - **Description**: The interval in seconds between successive checks for new time slots.
  - **Default Value**: `300` (5 minutes)

### Example Configuration

Here’s an example of how you might configure the `MonitorConfiguration`:

```json
{
  "license_types": ["B", "AM"],
  "exam_center_ids": [1, 7, 8],
  "seconds_inbetween": 600
}
```

## Possible Flow of the API

1. **Starting Monitoring**

   - User sends a `POST` request to `/startup` with the desired configuration.
   - System initializes or updates the monitoring configuration and starts the monitoring task.
   - System responds with a success or failure message.

2. **Updating Configuration**

   - User sends a `POST` request to `/monitor-config` with updated settings.
   - System updates the configuration and returns the current status of the monitoring task.

3. **Checking Status**

   - User sends a `GET` request to `/monitor-status`.
   - System returns the current status of the monitoring task, including runtime and any exceptions.

4. **Stopping Monitoring**

   - User sends a `GET` request to `/shutdown`.
   - System stops the monitoring task and returns a success or failure message.

5. **Managing Subscriptions**

   - User sends `POST` requests to `/subscribe` or `/unsubscribe` to manage email subscriptions.
   - System updates the subscription list and responds with the success status.

6. **Querying the Database**

   - User sends `GET` requests to `/request` or `/exam-time-slots` to retrieve records from the database.
   - System returns the requested data in JSON format.
