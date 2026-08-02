# Variables Configuration

This file contains the necessary configurations for the integration and deployment of the application. Make sure to keep this information secure and do not share it publicly.

## Environment Variables

### Application Configuration Variables

- **`FLASK_ENV`**:
  - **Description**: Flask environment configuration for the application (development, production, testing).
  - **Example**: `development`

- **`FLASK_DEBUG`**:
  - **Description**: Flask debug configuration for the application. Set to `1` for debugging or `0` for production mode.
  - **Example**: `0`

- **`SONARR_API_URL`**:
  - **Description**: The URL for the Sonarr API.
  - **Example**: `http://localhost:8989/api`

### Docker Configuration Variables

- **`DOCKER_NETWORK_STRAPERR`**:
  - **Description**: The name of the Docker network the deployed container joins.
  - **Example**: `straperr_network`

- **`DOCKER_HEALTHCHECK_URL`**:
  - **Description**: The URL to use for the Docker healthcheck.
  - **Example**: `http://localhost:5000/status`

- **`DOCKER_MEMORY_LIMIT`**:
  - **Description**: The memory limit for the Docker container. The container
    runs a headless Chromium (Selenium) for the HD-Olimpo login on top of the
    Flask app, so this needs meaningfully more headroom than a plain API
    service.
  - **Example**: `700M`

- **`DOCKER_MEMORY_RESERVATION`**:
  - **Description**: The memory reservation for the Docker container.
  - **Example**: `300M`


