from fastapi.testclient import TestClient
from api.app import app
from unittest.mock import AsyncMock, MagicMock, patch
from providers.generic import GenericOpenAIProvider


def test_root():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_create_message_streams():
    """Test that the /v1/messages endpoint returns a streaming response."""
    mock_provider = MagicMock(spec=GenericOpenAIProvider)

    async def mock_stream(*args, **kwargs):
        yield 'event: message_start\ndata: {"type":"message_start","message":{"id":"msg_1","type":"message","role":"assistant","model":"test","content":[],"usage":{"input_tokens":10,"output_tokens":0}}}\n\n'
        yield 'event: content_block_start\ndata: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}\n\n'
        yield 'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}\n\n'
        yield 'event: content_block_stop\ndata: {"type":"content_block_stop","index":0}\n\n'
        yield 'event: message_delta\ndata: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":5}}\n\n'
        yield 'event: message_stop\ndata: {"type":"message_stop"}\n\n'

    mock_provider.stream_response = mock_stream

    with patch("api.routes.get_provider_for_type", return_value=mock_provider):
        client = TestClient(app)
        payload = {
            "model": "claude-3-sonnet",
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 100,
        }
        response = client.post("/v1/messages", json=payload)
        assert response.status_code == 200
        assert "text_delta" in response.text


def test_error_fallbacks():
    from providers.exceptions import (
        AuthenticationError,
        RateLimitError,
        OverloadedError,
    )

    mock_provider = MagicMock(spec=GenericOpenAIProvider)

    # 1. Provider Authentication Error (401)
    mock_provider.stream_response = MagicMock(side_effect=AuthenticationError("Invalid Key"))
    with patch("api.routes.get_provider_for_type", return_value=mock_provider):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/v1/messages", json={"model": "test", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 10}
        )
        assert response.status_code == 401
        assert response.json()["error"]["type"] == "authentication_error"

    # 2. Rate Limit (429)
    mock_provider.stream_response = MagicMock(side_effect=RateLimitError("Too Many Requests"))
    with patch("api.routes.get_provider_for_type", return_value=mock_provider):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/v1/messages", json={"model": "test", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 10}
        )
        assert response.status_code == 429
        assert response.json()["error"]["type"] == "rate_limit_error"

    # 3. Overloaded (529)
    mock_provider.stream_response = MagicMock(side_effect=OverloadedError("Server Overloaded"))
    with patch("api.routes.get_provider_for_type", return_value=mock_provider):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/v1/messages", json={"model": "test", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 10}
        )
        assert response.status_code == 529
        assert response.json()["error"]["type"] == "overloaded_error"
