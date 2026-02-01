# 1. Use a slim python image for a smaller footprint
FROM python:3.12-slim

# Prevent python from writing .pyc files and enabling unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.2 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_HOME="/opt/poetry"


# Install system dependency required for postgres and building package
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir psycopg2


# Install poetry via official script
ENV POETRY_HOME=/opt/poetry
RUN curl -sSL https://install.python-poetry.org | python3 - --version $POETRY_VERSION && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry

# Set the working directory inside the container
WORKDIR /app

# Copy only dependency files first
COPY pyproject.toml poetry.lock* /app/

# Install dependencies without creating a virtualenv (Docker is alredy isolated)
RUN poetry install --no-interaction --no-ansi --no-root


# Copy the rest of application code
COPY . /app

# Export the port FastAPI runs on
EXPOSE 8000

# Start the server with hot-reload enabled for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]