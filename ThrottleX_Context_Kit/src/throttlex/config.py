"""Configuration settings for ThrottleX."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_prefix="THROTTLEX_", env_file=".env")

    # Server
    host: str = "127.0.0.1"  # Use THROTTLEX_HOST=0.0.0.0 for Docker
    port: int = 8080
    debug: bool = False

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0
    redis_pool_size: int = 50

    # Rate Limiting defaults
    default_algorithm: str = "SLIDING_WINDOW"
    default_limit: int = 100
    default_window_seconds: int = 60

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Metrics
    metrics_enabled: bool = True
    metrics_port: int = 9090


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
