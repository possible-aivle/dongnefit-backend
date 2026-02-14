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

    # -----------------------------------------
    # Backend
    # -----------------------------------------

    app_name: str = "DongneFit Backend"
    backend_url: str = "http://localhost:8000"
    api_v1_prefix: str = "/api/v1"
    debug: bool = False

    # Session
    secret_key: str = "your-secret-key-change-in-production"
    session_expire_days: int = 7

    # -----------------------------------------
    # Frontend
    # -----------------------------------------

    # App Url
    frontend_client_app_url: str = "http://localhost:5173"
    frontend_admin_app_url: str = "http://localhost:5174"

    # -----------------------------------------
    # Database
    # -----------------------------------------

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/dongnefit"
    database_echo: bool = False

    # -----------------------------------------
    # 공공데이터
    # -----------------------------------------

# 공공데이터포털 API 키 (https://www.data.go.kr/)
    data_go_kr_api_encode_key: str = ''
    data_go_kr_api_decode_key: str = ''

    # VWORLD API 키 (https://www.vworld.kr/)
    vworld_api_key: str = ''

    # KOSIS Open API (https://KOSIS.kostat.go.kr/)
    kosis_api_key: str = ''

    # 한국부동산원 R-ONE 부동산통계정보 API (https://www.reb.or.kr/r-one/portal/openapi/openApiIntroPage.do)
    r_one_api_key: str = ''

    # 데이터 저장 경로 (기본값: ./data)
    data_dir: str = './pipeline/data'


    # -----------------------------------------
    # THIRD PARTY
    # -----------------------------------------

    # OAuth - Google
    google_client_id: str = ""
    google_client_secret: str = ""
    google_callback_url: str = "http://localhost:8000/api/auth/google/callback"

    # OAuth - Kakao
    kakao_client_id: str = ""
    kakao_client_secret: str = ""
    kakao_callback_url: str = "http://localhost:8000/api/auth/kakao/callback"

    # OpenAI
    openai_api_key: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    # Map Service (e.g., Naver, Google)
    map_api_key: str = ""
    map_provider: str = "naver"  # naver, google

    # -----------------------------------------
    # 인프라
    # -----------------------------------------

    # AWS S3
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "ap-northeast-2"
    s3_bucket: str = ""

    # -----------------------------------------
    # 크롤링, 블로그, 자동화
    # -----------------------------------------

    # Selenium
    selenium_headless: bool = True
    selenium_timeout: int = 30

    # Tistory Credentials
    tistory_id: str = ""
    tistory_password: str = ""


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
