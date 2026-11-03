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
        env_ignore_empty=True,
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
    basal_threshold: float = Field(default=0.9, ge=0, le=1)
    basal_threshold_profiler: float | None = Field(default=None, ge=0, le=1)
    basal_threshold_in_role: float | None = Field(default=None, ge=0, le=1)
    basal_mode_profiler: Literal["off", "shadow", "live"] | None = None
    basal_mode_in_role: Literal["off", "shadow", "live"] | None = None
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
        """Profiler Basal mode (kept for existing callers)."""
        return self.basal_mode_for("profiler.attack_type")

    def basal_mode_for(self, node: str) -> Literal["off", "shadow", "live"]:
        """Basal mode for a decision node; "off" when no Basal URL is set."""
        if not self.basal_url:
            return "off"
        override = {
            "profiler.attack_type": self.basal_mode_profiler,
            "response.in_role": self.basal_mode_in_role,
        }.get(node)
        return override if override is not None else self.basal_mode

    def basal_threshold_for(self, node: str) -> float:
        """Confidence threshold for a decision node."""
        override = {
            "profiler.attack_type": self.basal_threshold_profiler,
            "response.in_role": self.basal_threshold_in_role,
        }.get(node)
        return override if override is not None else self.basal_threshold


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
