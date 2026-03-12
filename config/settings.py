"""Centralized configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .nim import NimSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ==================== Provider Config ====================
    provider_api_key: str = ""
    provider_base_url: str = "https://api.openai.com/v1"

    # ==================== Multi-Provider Keys ====================
    nvidia_nim_api_key: str = ""
    open_router_api_key: str = Field(default="", validation_alias="OPENROUTER_API_KEY")
    lm_studio_base_url: str = Field(default="http://localhost:1234/v1", validation_alias="LM_STUDIO_BASE_URL")
    llamacpp_base_url: str = Field(default="http://localhost:8080/v1", validation_alias="LLAMACPP_BASE_URL")

    # ==================== Model ====================
    # All Claude model requests are mapped to this single model
    model: str = "moonshotai/kimi-k2.5"

    # ==================== Model Overrides per Claude Tier ====================
    model_opus: Optional[str] = Field(default=None, validation_alias="MODEL_OPUS")
    model_sonnet: Optional[str] = Field(default=None, validation_alias="MODEL_SONNET")
    model_haiku: Optional[str] = Field(default=None, validation_alias="MODEL_HAIKU")

    # ==================== Rate Limiting ====================
    provider_rate_limit: int = 40
    provider_rate_window: int = 60

    # ==================== Fast Prefix Detection ====================
    fast_prefix_detection: bool = True

    # ==================== Logging ====================
    log_full_payloads: bool = False
    log_file: str = "server.log"

    # ==================== HTTP / Concurrency ====================
    provider_max_concurrency: int = 5
    http_read_timeout: float = 300.0
    http_write_timeout: float = 10.0
    http_connect_timeout: float = 2.0

    # ==================== Optimizations ====================
    enable_network_probe_mock: bool = True
    enable_title_generation_skip: bool = True
    enable_suggestion_mode_skip: bool = True
    enable_filepath_extraction_mock: bool = True

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

    # ==================== NVIDIA NIM ====================
    nim: NimSettings = Field(default_factory=NimSettings)

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
        "model_opus",
        "model_sonnet",
        "model_haiku",
        mode="before",
    )
    @classmethod
    def parse_optional_str(cls, v):
        if v == "":
            return None
        return v

    # ==================== Derived Helpers ====================

    @property
    def provider_type(self) -> str:
        """Extract provider type from the model string, or 'generic' if no known prefix."""
        known_providers = ("nvidia_nim", "open_router", "lmstudio", "llamacpp")
        if "/" in self.model:
            prefix = self.model.split("/", 1)[0]
            if prefix in known_providers:
                return prefix
        return "generic"

    @property
    def model_name(self) -> str:
        """Extract the actual model name from the model string."""
        known_providers = ("nvidia_nim", "open_router", "lmstudio", "llamacpp")
        if "/" in self.model:
            prefix = self.model.split("/", 1)[0]
            if prefix in known_providers:
                return self.model.split("/", 1)[1]
        return self.model

    def resolve_model(self, claude_model_name: str) -> str:
        """Resolve a Claude model name to the configured provider/model string."""
        name_lower = claude_model_name.lower()
        if "opus" in name_lower and self.model_opus is not None:
            return self.model_opus
        if "haiku" in name_lower and self.model_haiku is not None:
            return self.model_haiku
        if "sonnet" in name_lower and self.model_sonnet is not None:
            return self.model_sonnet
        return self.model

    @staticmethod
    def parse_provider_type(model_string: str) -> str:
        """Extract provider type from any 'provider/model' string, or 'generic'."""
        known_providers = ("nvidia_nim", "open_router", "lmstudio", "llamacpp")
        if "/" in model_string:
            prefix = model_string.split("/", 1)[0]
            if prefix in known_providers:
                return prefix
        return "generic"

    @staticmethod
    def parse_model_name(model_string: str) -> str:
        """Extract model name from any 'provider/model' string."""
        known_providers = ("nvidia_nim", "open_router", "lmstudio", "llamacpp")
        if "/" in model_string:
            prefix = model_string.split("/", 1)[0]
            if prefix in known_providers:
                return model_string.split("/", 1)[1]
        return model_string

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
