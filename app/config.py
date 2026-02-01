"""Application configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "DongneFit Backend"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/dongnefit"
    database_echo: bool = False

    # Session
    secret_key: str = "your-secret-key-change-in-production"
    session_expire_days: int = 7

    # OAuth - Google
    google_client_id: str = ""
    google_client_secret: str = ""

    # OAuth - Kakao
    kakao_client_id: str = ""
    kakao_client_secret: str = ""

    # OpenAI
    openai_api_key: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    # Map Service (e.g., Naver, Google)
    map_api_key: str = ""
    map_provider: str = "naver"  # naver, google

    # Toss Payments
    toss_client_key: str = ""
    toss_secret_key: str = ""
    toss_webhook_secret: str = ""

    # AWS S3
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "ap-northeast-2"
    s3_bucket: str = ""

    # Selenium
    selenium_headless: bool = True
    selenium_timeout: int = 30


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
