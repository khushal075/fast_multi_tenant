import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# ENV=local  → reads config.local.env  (local dev, Postgres at localhost)
# ENV=docker → reads config.env        (inside Docker, Postgres at 'db')
# Defaults to 'local' so running alembic/seed locally works without any setup
_env = os.getenv("ENV", "local")
_env_file = "config.local.env" if _env == "local" else "config.env"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Multi-Tenant Platform"
    API_V1_STR: str = "/api/v1"

    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=_env_file,
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()