# SBAT Monitoring System

## Overview

The **SBAT Monitoring System** is a Python API designed to monitor and notify users of available driving exam dates from the SBAT API. The system periodically checks for new available dates and sends notifications via email and Telegram when new dates are found. It also tracks the total runtime and provides status updates on the monitoring process.

## Table of Contents

- [Features](#features)
- [Design Choices](#design-choices)
- [API Endpoints](#api-endpoints)
- [Possible Flow of the API](#possible-flow-of-the-api)

## Features

- **Authentication**: Uses SBAT API credentials to authenticate and retrieve data.
- **Date Checking**: Periodically checks for available driving exam dates.
- **Notifications**: Sends notifications via email and Telegram when new dates are found.
- **Monitoring Status**: Provides information about the monitoring task's status, including runtime and exceptions.

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

- **`GET /exam-dates`**

  Retrieves all exam date records from the database.

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

   - User sends `GET` requests to `/request` or `/exam-dates` to retrieve records from the database.
   - System returns the requested data in JSON format.
