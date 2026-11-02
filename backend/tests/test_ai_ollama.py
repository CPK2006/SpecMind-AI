import json

import httpx
import pytest

from app.ai.gemini_service import (
    AIProviderUnavailableError,
    GeminiService,
)
from app.core.config import settings


@pytest.fixture(autouse=True)
def provider_settings(monkeypatch):
    monkeypatch.setattr(settings, "ollama_base_url", "http://localhost:11434")
    monkeypatch.setattr(settings, "ollama_model", "gemma3:4b")
    monkeypatch.setattr(settings, "ollama_timeout_seconds", 300.0)
    monkeypatch.setattr(settings, "gemini_api_key1", "")
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "gemini_api_keys", "")
    monkeypatch.setattr(settings, "nvidia_api_key", "")
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    GeminiService._provider_cooldowns.clear()
    GeminiService._gemini_next_key = 0


def test_ollama_response_is_parsed_as_json(monkeypatch):
    generated = {"functional_requirements": [{"title": "Book an appointment"}]}
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return httpx.Response(
            200,
            json={"response": json.dumps(generated), "done": True},
        )

    monkeypatch.setattr("app.ai.gemini_service.httpx.post", fake_post)
    result = GeminiService()._generate_json(
        "Generate requirements",
        preferred_provider="ollama",
    )

    assert result["functional_requirements"] == generated["functional_requirements"]
    assert result["ai_provider"] == "ollama"
    assert result["ai_model"] == "gemma3:4b"
    assert calls[0][0] == "http://localhost:11434/api/generate"
    assert calls[0][1]["json"]["stream"] is False
    assert calls[0][1]["json"]["format"] == "json"


@pytest.mark.parametrize(
    "failure",
    [httpx.ConnectError("local Ollama unavailable"), httpx.ReadTimeout("local inference timeout")],
)
def test_ollama_connection_or_timeout_falls_back_to_existing_provider(monkeypatch, failure):
    settings.nvidia_api_key = "nvidia-test"
    calls = []

    def fake_request(provider, model, key, prompt):
        calls.append(provider)
        if provider == "ollama":
            raise failure
        return '{"ok":true}'

    monkeypatch.setattr(GeminiService, "_request_provider", staticmethod(fake_request))
    result = GeminiService()._generate_json("prompt", preferred_provider="ollama")

    assert result["ok"] is True
    assert result["ai_provider"] == "nvidia"
    assert calls == ["ollama", "nvidia"]


@pytest.mark.parametrize(
    "ollama_body",
    [
        {"done": True},
        {"response": "not valid JSON", "done": True},
    ],
)
def test_malformed_ollama_output_uses_provider_failure_convention(monkeypatch, ollama_body):
    monkeypatch.setattr(
        "app.ai.gemini_service.httpx.post",
        lambda *args, **kwargs: httpx.Response(200, json=ollama_body),
    )

    with pytest.raises(AIProviderUnavailableError, match="ollama: unusable JSON response"):
        GeminiService()._generate_json("prompt", preferred_provider="ollama")


def test_pitch_generation_normalizes_ollama_result_shape(monkeypatch):
    calls = []
    response = {
        "functional_requirements": [
            {"title": "Book an appointment", "description": "Patients can book appointments."}
        ],
        "non_functional_requirements": [],
        "diagram_sources": {
            "class_diagram": "classDiagram\\n  class Patient\\n  class Appointment\\n  Patient ||--o{ Appointment : books",
            "er_diagram": "erDiagram\\n  PATIENT ||--o{ APPOINTMENT : books",
            "architecture_diagram": "flowchart LR\\n  Patient --> BookingService --> Database",
            "use_case_diagram": "usecase-beta\\nactor Patient\\nsystemBoundary Clinic {\\n  UC1(\\\"Book appointment\\\")\\n}\\nPatient --> UC1",
            "data_flow_diagram": "flowchart LR\\n  Patient --> Request --> BookingService --> Appointment",
            "sequence_diagram": "sequenceDiagram\\n  actor Patient\\n  Patient->>System: Book appointment\\n  System-->>Patient: Confirmation",
        },
    }

    def fake_request(provider, model, key, prompt):
        calls.append((provider, model))
        return json.dumps(response)

    monkeypatch.setattr(GeminiService, "_request_provider", staticmethod(fake_request))
    result = GeminiService().generate_srs_from_pitch("Patients can book appointments.")

    assert calls == [("ollama", "gemma3:4b")]
    assert "generation_status" not in result
    assert result["ai_provider"] == "ollama"
    assert result["functional_requirements"][0]["id"] == "FR-001"
    assert result["functional_requirements"][0]["origin"] == "generated"
    assert "class_diagram" in result["diagram_sources"]
    assert all(
        GeminiService.validate_diagram_source(name, source)[0]
        for name, source in result["diagram_sources"].items()
    )
    assert isinstance(result["test_cases"], list)


def test_pitch_generation_replaces_url_diagram_with_valid_local_source(monkeypatch):
    original_url = "https://mermaid.live/edit#2864ddc6-2578-40f4-83a4-b11711a95e5f"

    def fake_request(provider, model, key, prompt):
        if prompt.startswith("Return JSON only with one key named source"):
            assert provider == "ollama"
            return json.dumps({"source": "classDiagram\\n  class Librarian\\n  class Book\\n  Librarian --> Book : manages"})
        payload = {"diagram_sources": {"class_diagram": original_url}}
        return json.dumps(payload)

    monkeypatch.setattr(GeminiService, "_request_provider", staticmethod(fake_request))
    result = GeminiService().generate_srs_from_pitch("Librarians manage book intake and lending.")

    assert result["diagram_sources"]["class_diagram"].startswith("classDiagram\n")
    assert "diagram_generation_issues" not in result


def test_non_pilot_workflow_keeps_existing_provider_selection(monkeypatch):
    settings.nvidia_api_key = "nvidia-test"
    calls = []

    def fake_request(provider, model, key, prompt):
        calls.append(provider)
        return '{"is_software_document":true}'

    monkeypatch.setattr(GeminiService, "_request_provider", staticmethod(fake_request))
    result = GeminiService().analyze_requirements("A software requirements source.")

    assert result["ai_provider"] == "nvidia"
    assert calls == ["nvidia"]
