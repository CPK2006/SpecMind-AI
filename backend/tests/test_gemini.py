from app.ai.gemini_service import GeminiService
from app.core.config import settings


def test_json_generation_parses_provider_response(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(settings, "gemini_api_keys", "")
    monkeypatch.setattr(settings, "nvidia_api_key", "")
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    monkeypatch.setattr(GeminiService, "_request_provider", staticmethod(lambda *args: '{"functional_requirements": []}'))
    result = GeminiService()._generate_json("test prompt")
    assert result["functional_requirements"] == []
    assert result["ai_provider"] == "gemini"


def test_uploaded_srs_prompts_accept_project_context(monkeypatch):
    prompts = []
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(settings, "gemini_api_keys", "")
    monkeypatch.setattr(settings, "nvidia_api_key", "")
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    def fake_request(provider, model, key, prompt):
        prompts.append(prompt)
        return "{}"
    monkeypatch.setattr(GeminiService, "_request_provider", staticmethod(fake_request))
    service = GeminiService()

    service.analyze_requirements("source text", "Campus users need mobile access")
    service.generate_clarification_questions("source text", "Campus users need mobile access")
    service.refactor_srs("source text", {"Q-001": "Use OIDC"}, "Campus users need mobile access")

    assert len(prompts) == 3
    assert all("Campus users need mobile access" in prompt for prompt in prompts)
    assert all("source text" in prompt for prompt in prompts)
    assert '"Q-001": "Use OIDC"' in prompts[-1]
