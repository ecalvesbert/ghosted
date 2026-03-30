from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://localhost/ghosted"
    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 72
    ENCRYPTION_KEY: str = ""  # Fernet key — required
    ADMIN_BOOTSTRAP_SECRET: str = ""
    BROWSERBASE_API_KEY: str = ""
    BROWSERBASE_PROJECT_ID: str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    FRONTEND_URL: str = "http://localhost:3000"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
