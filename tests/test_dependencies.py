import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from api.dependencies import get_provider, get_settings, cleanup_provider
from providers.generic import GenericOpenAIProvider


@pytest.fixture(autouse=True)
def reset_provider():
    """Reset the global _providers registry between tests."""
    with patch("api.dependencies._providers", {}):
        yield


def _make_mock_settings():
    """Create a mock settings object with all required attributes."""
    s = MagicMock()
    s.provider_api_key = "test_key"
    s.provider_base_url = "https://test.api.com/v1"
    s.provider_rate_limit = 40
    s.provider_rate_window = 60
    s.provider_max_concurrency = 5
    s.http_read_timeout = 300.0
    s.http_write_timeout = 10.0
    s.http_connect_timeout = 2.0
    s.provider_type = "generic"
    s.provider_temperature = 1.0
    s.provider_top_p = 1.0
    s.provider_top_k = -1
    s.provider_max_tokens = 81920
    s.provider_presence_penalty = 0.0
    s.provider_frequency_penalty = 0.0
    s.provider_min_p = 0.0
    s.provider_repetition_penalty = 1.0
    s.provider_seed = None
    s.provider_stop = None
    s.provider_parallel_tool_calls = True
    s.provider_return_tokens_as_token_ids = False
    s.provider_include_stop_str_in_output = False
    s.provider_ignore_eos = False
    s.provider_min_tokens = 0
    s.provider_chat_template = ""
    s.provider_request_id = ""
    s.provider_reasoning_effort = "high"
    s.provider_include_reasoning = True
    return s


@pytest.mark.asyncio
async def test_get_provider_singleton():
    with patch("api.dependencies.get_settings") as mock_get_settings:
        mock_get_settings.return_value = _make_mock_settings()

        p1 = get_provider()
        p2 = get_provider()

        assert isinstance(p1, GenericOpenAIProvider)
        assert p1 is p2


@pytest.mark.asyncio
async def test_get_settings():
    settings = get_settings()
    assert settings is not None
    # Verify it calls the internal _get_settings
    with patch("api.dependencies._get_settings") as mock_get:
        get_settings()
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_provider():
    with patch("api.dependencies.get_settings") as mock_get_settings:
        mock_get_settings.return_value = _make_mock_settings()

        provider = get_provider()
        provider._client = AsyncMock()

        await cleanup_provider()

        provider._client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_provider_no_client():
    with patch("api.dependencies.get_settings") as mock_get_settings:
        mock_get_settings.return_value = _make_mock_settings()

        provider = get_provider()
        if hasattr(provider, "_client"):
            del provider._client

        await cleanup_provider()
        # Should not raise
