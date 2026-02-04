"""Dependency injection for FastAPI."""

from typing import Optional
from config.settings import Settings, get_settings as _get_settings
from providers.base import ProviderConfig
from providers.openai_provider import OpenAIProvider


# Global provider instance (singleton)
_provider: Optional[OpenAIProvider] = None


def get_settings() -> Settings:
    """Get application settings via dependency injection."""
    return _get_settings()


def get_provider() -> OpenAIProvider:
    """Get or create the provider instance."""
    global _provider
    if _provider is None:
        settings = get_settings()
        config = ProviderConfig(
            api_key=settings.provider_api_key,
            base_url=settings.provider_base_url,
            rate_limit=settings.provider_rate_limit,
            rate_window=settings.provider_rate_window,
        )
        _provider = OpenAIProvider(config)
    return _provider


async def cleanup_provider():
    """Cleanup provider resources."""
    global _provider
    if _provider:
        client = getattr(_provider, "_client", None)
        if client and hasattr(client, "aclose"):
            await client.aclose()
    _provider = None
