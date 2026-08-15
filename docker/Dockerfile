# Use an official Python base image
FROM python:3.15.0rc1-alpine3.23

# Set environment variables to ensure Python output is sent straight to the terminal
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# Chromium local para el login de HD-Olimpo (sin contenedor Selenium externo)
ENV CHROME_BIN=/usr/bin/chromium-browser \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Update the package index and upgrade installed packages
RUN apk update && apk upgrade

# Install the required system packages
RUN apk add --no-cache \
    curl \
    chromium \
    chromium-chromedriver

# Create a non-privileged user to run the application
RUN adduser -D -s /bin/sh python

# Set the working directory for subsequent commands
WORKDIR /app

# Change the ownership of the working directory to the non-privileged user
RUN chown python:python /app

# Copy the requirements file to the container and install dependencies
COPY --chown=python:python src/requirements.txt .

# Instala pytest y flake8 solo cuando se construye para desarrollo local
# (docker/compose.yml pasa INSTALL_DEV_TOOLS=true); la imagen de producción
# no los necesita.
ARG INSTALL_DEV_TOOLS=false

# Upgrade pip and install Python dependencies specified in the requirements file
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    if [ "$INSTALL_DEV_TOOLS" = "true" ]; then \
        pip install --no-cache-dir pytest flake8; \
    fi

# Copy the application code into the container
COPY --chown=python:python src/ .

# Expose port 5000 for the application
EXPOSE 5000

# Change the user to the non-privileged user
USER python

# Run with Gunicorn: 2 workers is enough for a webhook receiver
# main:app  →  archivo main.py, objeto Flask llamado app
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "main:app"]
