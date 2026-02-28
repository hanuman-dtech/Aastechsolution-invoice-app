"""
Invoice Enterprise Console - Core Configuration

Environment-based configuration using Pydantic Settings.
"""

from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Invoice Enterprise Console"
    app_version: str = "1.0.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    secret_key: str = "change-this-in-production-use-openssl-rand-hex-32"
    
    # API
    api_v1_prefix: str = "/api"
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/invoice_enterprise"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    # SMTP (defaults can be overridden per-tenant in DB)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True
    
    # Security
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    password_min_length: int = 8
    
    # File Storage
    invoice_output_dir: str = "generated_invoices"
    max_upload_size_mb: int = 10
    
    @property
    def async_database_url(self) -> str:
        """Convert sync URL to async URL for async SQLAlchemy."""
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://")
    
    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
