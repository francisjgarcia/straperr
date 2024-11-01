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

### Docker Configuration Variables

- **`DOCKER_DNS1`**:
  - **Description**: The primary DNS server for Docker containers.
  - **Example**: `8.8.8.8`

- **`DOCKER_DNS2`**:
  - **Description**: The secondary DNS server for Docker containers.
  - **Example**: `8.8.4.4`

- **`DOCKER_NETWORK`**:
  - **Description**: The name of the Docker network to use for the application.
  - **Example**: `straperr_network`

- **`DOCKER_HEALTHCHECK_URL`**:
  - **Description**: The URL to use for the Docker healthcheck.
  - **Example**: `http://localhost:5000/health`

- **`DOCKER_MEMORY_LIMIT`**:
  - **Description**: The memory limit for the Docker container.
  - **Example**: `50M`

- **`DOCKER_MEMORY_RESERVATION`**:
  - **Description**: The memory reservation for the Docker container.
  - **Example**: `10M`
