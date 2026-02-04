"""Centralized configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

# Default base URL for provider (any OpenAI-compatible endpoint)
PROVIDER_BASE_URL = "https://api.openai.com/v1"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ==================== Provider Config ====================
    provider_api_key: str = ""
    provider_base_url: str = PROVIDER_BASE_URL

    # ==================== Model ====================
    # All Claude model requests are mapped to this single model
    model: str = "moonshotai/kimi-k2.5"

    # ==================== Rate Limiting ====================
    provider_rate_limit: int = 40
    provider_rate_window: int = 60

    # ==================== Fast Prefix Detection ====================
    fast_prefix_detection: bool = True

    # ==================== Logging ====================
    log_full_payloads: bool = False

    # ==================== Optimizations ====================
    enable_network_probe_mock: bool = True
    enable_title_generation_skip: bool = True

    # ==================== Provider Core Parameters ====================
    provider_temperature: float = 1.0
    provider_top_p: float = 1.0
    provider_top_k: int = -1
    provider_max_tokens: int = 81920
    provider_presence_penalty: float = 0.0
    provider_frequency_penalty: float = 0.0

    # ==================== Provider Advanced Parameters ====================
    provider_min_p: float = 0.0
    provider_repetition_penalty: float = 1.0
    provider_seed: Optional[int] = None
    provider_stop: Optional[str] = None

    # ==================== Provider Flag Parameters ====================
    provider_parallel_tool_calls: bool = True
    provider_return_tokens_as_token_ids: bool = False
    provider_include_stop_str_in_output: bool = False
    provider_ignore_eos: bool = False

    provider_min_tokens: int = 0
    provider_chat_template: str = ""
    provider_request_id: str = ""

    # ==================== Thinking/Reasoning Parameters ====================
    provider_reasoning_effort: str = "high"
    provider_include_reasoning: bool = True

    # ==================== Bot Wrapper Config ====================
    telegram_bot_token: Optional[str] = None
    telegram_api_id: Optional[str] = None  # Deprecated
    telegram_api_hash: Optional[str] = None  # Deprecated
    allowed_telegram_user_id: Optional[str] = None
    claude_workspace: str = "./agent_workspace"
    allowed_dir: str = ""
    max_cli_sessions: int = 10

    # ==================== Server ====================
    host: str = "0.0.0.0"
    port: int = 8082

    # ==================== MongoDB ====================
    mongodb_uri: str = "mongodb://localhost:27017"

    # ==================== SMTP (Email) ====================
    smtp_host: Optional[str] = None  # If None, print code to console
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None

    # Handle empty strings for optional int fields
    @field_validator("provider_seed", mode="before")
    @classmethod
    def parse_optional_int(cls, v):
        if v == "" or v is None:
            return None
        return int(v)

    # Handle empty strings for optional string fields
    @field_validator(
        "provider_stop",
        "telegram_bot_token",
        "telegram_api_id",
        "telegram_api_hash",
        "allowed_telegram_user_id",
        "smtp_host",
        "smtp_user",
        "smtp_password",
        "smtp_from_email",
        mode="before",
    )
    @classmethod
    def parse_optional_str(cls, v):
        if v == "":
            return None
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
