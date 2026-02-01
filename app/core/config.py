import os
from typing import List, Union

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    project_name: str = 'Multi-tenant platform'
    API_V1_STR: str = "/api/v1"

    POSTGRES_SERVER: str  # e.g., "db" (the Docker service name)
    POSTGRES_USER: str  # e.g., "postgres"
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    # Property engine uses to connect
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        # return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
        return os.getenv("DATABASE_URL", "postgresql://local:local@db:5432/app_db")

    # Tell pydantic to read from .env file
    model_config = SettingsConfigDict(env_file='config.env', case_sensitive=True, extra='ignore')


# Initialize it once so that it is singleton across the whole app
settings = Settings()