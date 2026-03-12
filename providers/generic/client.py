"""Generic OpenAI-compatible provider implementation."""

from typing import Any

from providers.base import ProviderConfig
from providers.openai_compat import OpenAICompatibleProvider

from .request import build_request_body
from .settings import GenericProviderSettings


class GenericOpenAIProvider(OpenAICompatibleProvider):
    """Provider that works with any OpenAI-compatible API."""

    def __init__(
        self,
        config: ProviderConfig,
        *,
        generic_settings: GenericProviderSettings | None = None,
    ):
        super().__init__(
            config,
            provider_name="GENERIC",
            base_url=config.base_url or "https://api.openai.com/v1",
            api_key=config.api_key,
        )
        self._generic_settings = generic_settings or GenericProviderSettings()

    def _build_request_body(self, request: Any) -> dict:
        """Build OpenAI-format request body from Anthropic request."""
        return build_request_body(request, self._generic_settings)
