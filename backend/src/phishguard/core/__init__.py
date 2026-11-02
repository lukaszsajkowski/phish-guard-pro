"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Load .env from project root (parent of backend directory)
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent.parent.parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Supabase - use alias to read NEXT_PUBLIC_* vars from shared .env
    supabase_url: str = Field(default="", validation_alias="NEXT_PUBLIC_SUPABASE_URL")
    supabase_anon_key: str = Field(
        default="", validation_alias="NEXT_PUBLIC_SUPABASE_ANON_KEY"
    )
    supabase_service_role_key: str = ""
    supabase_db_url: str = ""  # Direct PostgreSQL connection URL for checkpointing

    # OpenAI
    openai_api_key: str = ""
    openai_primary_model: str = "gpt-4o"
    openai_fallback_model: str = "gpt-4o-mini"

    # IOC Enrichment API keys (optional — enrichment degrades gracefully when absent)
    bitcoinabuse_api_key: str = ""
    virustotal_api_key: str = ""
    abuseipdb_api_key: str = ""
    numverify_api_key: str = ""

    # Basal local decision layer (empty URL behaves like mode "off")
    basal_url: str = ""
    basal_mode: Literal["off", "shadow", "live"] = "shadow"
    basal_threshold: float = 0.9
    basal_threshold_profiler: float | None = None
    basal_timeout_s: float = 30.0
    basal_model: str = ""

    # Application
    debug: bool = False
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def basal_effective_mode(self) -> Literal["off", "shadow", "live"]:
        """Basal mode, forced to "off" when no Basal URL is configured."""
        return self.basal_mode if self.basal_url else "off"

    def basal_threshold_for(self, node: str) -> float:
        """Confidence threshold for a decision node."""
        if node == "profiler.attack_type" and self.basal_threshold_profiler is not None:
            return self.basal_threshold_profiler
        return self.basal_threshold


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
