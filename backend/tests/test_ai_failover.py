import pytest

from app.ai.gemini_service import (
    AIProviderUnavailableError,
    BillingProviderError,
    GeminiService,
    ProviderHTTPError,
)
from app.core.config import settings


@pytest.fixture(autouse=True)
def provider_settings(monkeypatch):
    monkeypatch.setattr(settings, "nvidia_api_key", "")
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    monkeypatch.setattr(settings, "nvidia_model", "z-ai/glm-5.3")
    monkeypatch.setattr(settings, "openrouter_model", "openrouter/auto")
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "gemini_api_keys", "")
    GeminiService._provider_cooldowns.clear()
    GeminiService._gemini_next_key = 0


def test_provider_order_and_invalid_json_failover(monkeypatch):
    settings.nvidia_api_key = "nvidia-test"
    settings.openrouter_api_key = "router-test"
    settings.gemini_api_keys = "gemini-a,gemini-b"
    calls = []

    def request(provider, model, key, prompt):
        calls.append((provider, model))
        return "not-json" if provider == "nvidia" else '{"ok":true}'

    monkeypatch.setattr(GeminiService, "_request_provider", staticmethod(request))
    assert GeminiService()._generate_json("prompt")["ai_provider"] == "openrouter"
    assert [provider for provider, _ in calls] == ["nvidia", "openrouter"]
    assert calls[1][1] == "openrouter/auto"


def test_gemini_starting_key_rotates_and_second_key_is_same_request_fallback(monkeypatch):
    settings.gemini_api_keys = "key-a,key-b"
    calls = []

    def request(provider, model, key, prompt):
        calls.append(key)
        if key == "key-a":
            raise ProviderHTTPError(429, "0")
        return '{"ok":true}'

    monkeypatch.setattr(GeminiService, "_request_provider", staticmethod(request))
    service = GeminiService()
    assert service._generate_json("first")["ok"] is True
    # The next request starts with key B; it does not need key A.
    assert service._generate_json("second")["ok"] is True
    assert calls == ["key-a", "key-b", "key-b"]


def test_all_provider_failures_are_sanitized(monkeypatch):
    settings.nvidia_api_key = "secret-nvidia"
    settings.openrouter_api_key = "secret-router"

    def request(provider, model, key, prompt):
        raise TimeoutError()

    monkeypatch.setattr(GeminiService, "_request_provider", staticmethod(request))
    with pytest.raises(AIProviderUnavailableError) as caught:
        GeminiService()._generate_json("prompt")
    message = str(caught.value)
    assert "nvidia: network timeout" in message
    assert "openrouter: network timeout" in message
    assert "secret" not in message


@pytest.mark.parametrize("error", [ProviderHTTPError(401), ProviderHTTPError(429, "2"), TimeoutError()])
def test_auth_quota_and_network_failures_advance_to_next_provider(monkeypatch, error):
    settings.nvidia_api_key = "nvidia-test"
    settings.openrouter_api_key = "router-test"
    calls = []

    def request(provider, model, key, prompt):
        calls.append(provider)
        if provider == "nvidia":
            raise error
        return '{"ok":true}'

    monkeypatch.setattr(GeminiService, "_request_provider", staticmethod(request))
    assert GeminiService()._generate_json("prompt")["ai_provider"] == "openrouter"
    assert calls == ["nvidia", "openrouter"]


def test_deprecated_provider_model_410_is_reported_and_skipped(monkeypatch):
    settings.nvidia_api_key = "nvidia-test"
    settings.openrouter_api_key = "router-test"
    calls = []

    def request(provider, model, key, prompt):
        calls.append(provider)
        if provider == "nvidia":
            raise ProviderHTTPError(410)
        return '{"ok":true}'

    monkeypatch.setattr(GeminiService, "_request_provider", staticmethod(request))
    assert GeminiService()._generate_json("prompt")["ai_provider"] == "openrouter"
    assert calls == ["nvidia", "openrouter"]
    category, cooldown = GeminiService._classify_failure(ProviderHTTPError(410))
    assert "no longer available" in category
    assert cooldown == 3600


def test_pitch_returns_source_based_draft_after_every_provider_fails(monkeypatch):
    settings.nvidia_api_key = "nvidia-test"

    def request(*args):
        raise TimeoutError()

    monkeypatch.setattr(GeminiService, "_request_provider", staticmethod(request))
    result = GeminiService().generate_srs_from_pitch("A service that helps users reserve appointments.")
    assert result["generation_status"] == "draft"
    assert "nvidia: network timeout" in result["generation_note"]
    assert result["functional_requirements"]


def test_billing_error_skips_provider_and_continues_failover(monkeypatch):
    settings.nvidia_api_key = "nvidia-test"
    settings.openrouter_api_key = "router-test"
    settings.gemini_api_key = "gemini-test"
    calls = []

    def request(provider, model, key, prompt):
        calls.append(provider)
        if provider == "nvidia":
            raise ProviderHTTPError(410)
        if provider == "openrouter":
            raise BillingProviderError()
        return '{"ok":true}'

    monkeypatch.setattr(GeminiService, "_request_provider", staticmethod(request))
    result = GeminiService()._generate_json("prompt")
    assert result["ai_provider"] == "gemini"
    assert calls == ["nvidia", "openrouter", "gemini"]

