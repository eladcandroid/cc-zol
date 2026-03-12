from config.settings import Settings


def test_parse_model_name_strips_known_provider_prefix():
    assert Settings.parse_model_name("nvidia_nim/llama-3") == "llama-3"
    assert Settings.parse_model_name("open_router/gpt-4") == "gpt-4"
    assert Settings.parse_model_name("lmstudio/gemma") == "gemma"
    assert Settings.parse_model_name("llamacpp/phi") == "phi"


def test_parse_model_name_unknown_prefix_unchanged():
    # Unknown prefixes (including "anthropic/", "openai/") are NOT stripped
    assert Settings.parse_model_name("anthropic/claude-3") == "anthropic/claude-3"
    assert Settings.parse_model_name("openai/gpt-4") == "openai/gpt-4"
    assert Settings.parse_model_name("no-prefix") == "no-prefix"


def test_resolve_model_opus(monkeypatch):
    monkeypatch.setenv("PROVIDER_API_KEY", "test")
    monkeypatch.setenv("MODEL", "default-model")
    monkeypatch.setenv("MODEL_OPUS", "opus-override")
    s = Settings()
    assert s.resolve_model("claude-3-opus-20240229") == "opus-override"


def test_resolve_model_sonnet(monkeypatch):
    monkeypatch.setenv("PROVIDER_API_KEY", "test")
    monkeypatch.setenv("MODEL", "default-model")
    monkeypatch.setenv("MODEL_SONNET", "sonnet-override")
    s = Settings()
    assert s.resolve_model("claude-3-5-sonnet-20241022") == "sonnet-override"


def test_resolve_model_haiku(monkeypatch):
    monkeypatch.setenv("PROVIDER_API_KEY", "test")
    monkeypatch.setenv("MODEL", "default-model")
    monkeypatch.setenv("MODEL_HAIKU", "haiku-override")
    s = Settings()
    assert s.resolve_model("claude-3-haiku-20240307") == "haiku-override"


def test_resolve_model_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("PROVIDER_API_KEY", "test")
    monkeypatch.setenv("MODEL", "default-model")
    # No tier overrides set
    monkeypatch.delenv("MODEL_OPUS", raising=False)
    monkeypatch.delenv("MODEL_SONNET", raising=False)
    monkeypatch.delenv("MODEL_HAIKU", raising=False)
    s = Settings()
    assert s.resolve_model("claude-3-sonnet") == "default-model"
    assert s.resolve_model("claude-3-opus") == "default-model"
    assert s.resolve_model("claude-3-haiku") == "default-model"
    assert s.resolve_model("gpt-4") == "default-model"


def test_resolve_model_case_insensitive(monkeypatch):
    monkeypatch.setenv("PROVIDER_API_KEY", "test")
    monkeypatch.setenv("MODEL", "default-model")
    monkeypatch.setenv("MODEL_OPUS", "opus-override")
    s = Settings()
    assert s.resolve_model("Claude-3-Opus") == "opus-override"


def test_parse_provider_type():
    assert Settings.parse_provider_type("nvidia_nim/llama-3") == "nvidia_nim"
    assert Settings.parse_provider_type("open_router/gpt-4") == "open_router"
    assert Settings.parse_provider_type("lmstudio/gemma") == "lmstudio"
    assert Settings.parse_provider_type("llamacpp/phi") == "llamacpp"
    assert Settings.parse_provider_type("some-model") == "generic"
    assert Settings.parse_provider_type("openai/gpt-4") == "generic"
