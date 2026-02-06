"""Configuration settings for ThrottleX."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server
    host: str = "0.0.0.0"
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

    class Config:
        env_prefix = "THROTTLEX_"
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
