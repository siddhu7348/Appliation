from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = "ForecastIQ"
    api_prefix: str = "/api/v1"
    environment: str = "development"

    database_url: str = "sqlite+aiosqlite:///./forecastiq.db"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8

    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    artifacts_dir: Path = Path("/artifacts")
    cache_ttl_seconds: int = 60 * 60 * 12

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "alerts@forecastiq.io"
    smtp_starttls: bool = True
    alerts_enabled: bool = False

    anomaly_alert_threshold: float = 0.8
    anomaly_flag_threshold: float = 0.7
    coverage_target: float = 0.80
    drift_mape_threshold_pp: float = 5.0
    drift_consecutive_weeks: int = 3

    auth_rate_limit: str = "10/minute"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("+asyncpg", "").replace("+aiosqlite", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
