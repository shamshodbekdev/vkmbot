from pathlib import Path
from urllib.parse import unquote, urlparse

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
LOCALES_DIR: Path = BASE_DIR / "i18n"


class Configuration(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    telegram_token: SecretStr = Field(
        ...,
        alias="TELEGRAM_TOKEN",
        description="Telegram bot token",
    )
    telegram_username: str = Field(
        ...,
        alias="TELEGRAM_USERNAME",
        description="Telegram bot username",
    )
    telegram_id: int = Field(
        ...,
        alias="TELEGRAM_ID",
        description="Superadmin Telegram chat ID",
    )
    telegram_api_url: str = Field(
        "https://api.telegram.org",
        alias="TELEGRAM_API_URL",
        description="Telegram Bot API server URL",
    )
    telegram_api_local: bool = Field(
        False,
        alias="TELEGRAM_API_LOCAL",
        description="Set to true when TELEGRAM_API_URL points to a local Bot API server (--local mode)",
    )

    redis_url: str = Field(
        ...,
        alias="REDIS_URL",
        description="Redis connection URL",
    )
    database_url: str = Field(
        ...,
        alias="DATABASE_URL",
        description="Database connection URL",
    )

    @property
    def redis_options(self) -> dict:
        """Connection options parsed from REDIS_URL (host, port, db, username, password)."""
        parsed = urlparse(self.redis_url)
        path = parsed.path.lstrip("/")
        return dict(
            host=parsed.hostname or "localhost",
            port=parsed.port or 6379,
            db=int(path) if path.isdigit() else 0,
            username=unquote(parsed.username) if parsed.username else None,
            password=unquote(parsed.password) if parsed.password else None,
            ssl=parsed.scheme == "rediss",
        )


config = Configuration()
