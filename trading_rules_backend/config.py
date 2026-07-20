from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables or a .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "Helo"
    API_V1_PREFIX: str = "/api"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    LOGGER_NAME: str = "Backtest_Engine"


    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
