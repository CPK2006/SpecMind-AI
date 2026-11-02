from __future__ import annotations

import json
import hashlib
import re
import threading
import time
from collections.abc import Mapping
from logging import getLogger
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

from google import genai
from google.genai import errors as genai_errors
import httpx

from app.ai.prompts import (
    REQUIREMENT_ANALYSIS_PROMPT,
    TEST_CASE_PROMPT,
    REQUIREMENT_QUALITY_PROMPT,
    PITCH_SRS_PROMPT,
    CLARIFICATION_QUESTIONS_PROMPT,
    REFACTOR_SRS_PROMPT,
)
from app.core.config import settings

logger = getLogger(__name__)


class InvalidAIResponseError(Exception):
    pass


class BillingProviderError(Exception):
    pass


class ProviderHTTPError(Exception):
    def __init__(self, status_code: int, retry_after: str | None = None):
        self.status_code = status_code
        self.retry_after = retry_after


class AIProviderUnavailableError(RuntimeError):
    """Sanitized provider failures suitable for logs and user-facing draft notes."""

    def __init__(self, failures: list[str]):
        self.provider_failures = failures
        super().__init__("AI providers unavailable: " + "; ".join(failures))

    @property
    def public_summary(self) -> str:
        return "AI providers could not complete generation (" + "; ".join(self.provider_failures) + ")."


class GeminiService:
    MODEL_NAME = "gemini-2.5-flash"
    # Full SRS responses include requirements, tests, and several diagrams;
    # reasoning models can take longer than the former 45 second read timeout.
    PROVIDER_READ_TIMEOUT_SECONDS = 180
    _gemini_lock = threading.Lock()
    _gemini_next_key = 0
    _provider_cooldowns: dict[str, float] = {}

    def __init__(self):
        # Clients are created per key on demand. This avoids making an empty
        # Gemini key prevent NVIDIA/OpenRouter-only installations from starting.
        self.client = None

    def test_connection(self) -> str:
        result = self._generate_json(
            'Return JSON only: {"message":"SpecMind AI connected successfully."}'
        )
        return str(result.get("message") or "SpecMind AI connected successfully.")

    def _generate_json(
        self,
        prompt: str,
        *,
        preferred_provider: str | None = None,
        local_only: bool = False,
    ) -> dict:
        """
        Sends a prompt to the selected AI provider and returns parsed JSON.
        """

        failures: list[str] = []
        providers = self._configured_providers(preferred_provider=preferred_provider)
        if local_only:
            providers = [provider for provider in providers if provider[0] == "ollama"]
        if not providers:
            raise AIProviderUnavailableError(["No AI provider is configured"])

        for provider, model, key in providers:
            key_fingerprint = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
            cooldown_key = f"{provider}:{key_fingerprint}" if provider == "gemini" else provider
            if self._provider_cooldowns.get(cooldown_key, 0) > time.monotonic():
                failures.append(f"{provider}: temporarily cooling down after a recent rate limit")
                continue
            try:
                text = self._request_provider(provider, model, key, prompt)
                parsed = self._parse_json(text)
            except BillingProviderError:
                # Do not retry a provider with a billing problem, but preserve
                # the failover chain so another configured provider can serve the request.
                failures.append(f"{provider}: billing/payment error")
                self._provider_cooldowns[cooldown_key] = time.monotonic() + 300
                logger.warning("AI provider=%s model=%s failure=billing_payment", provider, model)
                continue
            except InvalidAIResponseError:
                failures.append(f"{provider}: unusable JSON response")
                logger.warning("AI provider=%s model=%s failure=invalid_json", provider, model)
                continue
            except Exception as exc:
                category, cooldown = self._classify_failure(exc)
                if cooldown:
                    self._provider_cooldowns[cooldown_key] = time.monotonic() + cooldown
                failures.append(f"{provider}: {category}")
                logger.warning(
                    "AI provider=%s model=%s failure=%s exception_type=%s",
                    provider,
                    model,
                    category,
                    type(exc).__name__,
                )
                continue

            logger.info("AI provider=%s model=%s outcome=success", provider, model)
            parsed.setdefault("ai_provider", provider)
            parsed.setdefault("ai_model", model)
            return parsed

        raise AIProviderUnavailableError(failures or ["All configured providers are cooling down"])

    @classmethod
    def _configured_providers(
        cls,
        *,
        preferred_provider: str | None = None,
    ) -> list[tuple[str, str, str]]:
        providers = []
        preferred_gemini_key = settings.gemini_api_key1.strip()
        raw_keys = [preferred_gemini_key, *settings.gemini_api_keys.split(","), settings.gemini_api_key]
        keys = list(dict.fromkeys(key.strip() for key in raw_keys if key.strip()))
        if keys:
            if preferred_gemini_key:
                keys = [preferred_gemini_key, *(key for key in keys if key != preferred_gemini_key)]
            else:
                with cls._gemini_lock:
                    start = cls._gemini_next_key % len(keys)
                    cls._gemini_next_key += 1
                keys = keys[start:] + keys[:start]
            gemini_providers = [("gemini", cls.MODEL_NAME, key) for key in keys]
            if preferred_gemini_key:
                providers.extend(gemini_providers)
        if settings.nvidia_api_key.strip():
            providers.append(("nvidia", settings.nvidia_model, settings.nvidia_api_key.strip()))
        if settings.openrouter_api_key.strip():
            providers.append(("openrouter", settings.openrouter_model, settings.openrouter_api_key.strip()))
        if keys and not preferred_gemini_key:
            providers.extend(gemini_providers)
        if preferred_provider == "ollama" and settings.ollama_base_url.strip():
            providers.insert(
                0,
                (
                    "ollama",
                    settings.ollama_model.strip() or "gemma3:4b",
                    settings.ollama_base_url.strip(),
                ),
            )
        return providers

    @staticmethod
    def _request_provider(provider: str, model: str, key: str, prompt: str) -> str:
        if provider == "ollama":
            base_url = key.rstrip("/")
            response = httpx.post(
                f"{base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
                timeout=httpx.Timeout(
                    connect=5.0,
                    read=settings.ollama_timeout_seconds,
                    write=30.0,
                    pool=5.0,
                ),
            )
            if response.status_code >= 400:
                raise ProviderHTTPError(
                    response.status_code,
                    response.headers.get("Retry-After"),
                )
            try:
                body = response.json()
            except ValueError as exc:
                raise InvalidAIResponseError() from exc
            if not isinstance(body, dict):
                raise InvalidAIResponseError()
            generated_text = body.get("response")
            if not isinstance(generated_text, str) or not generated_text.strip():
                raise InvalidAIResponseError()
            return generated_text

        if provider == "gemini":
            from google.genai import types
            client = genai.Client(
                api_key=key,
                http_options=types.HttpOptions(
                    timeout=GeminiService.PROVIDER_READ_TIMEOUT_SECONDS * 1_000,
                    retry_options=types.HttpRetryOptions(attempts=1),
                ),
            )
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            if not response.text:
                raise InvalidAIResponseError()
            return response.text

        url = "https://integrate.api.nvidia.com/v1/chat/completions" if provider == "nvidia" else "https://openrouter.ai/api/v1/chat/completions"
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}
        if provider == "openrouter":
            payload["plugins"] = [{"id": "auto-router", "cost_tier": "low"}]
        response = httpx.post(
            url,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
            timeout=httpx.Timeout(
                connect=15.0,
                read=GeminiService.PROVIDER_READ_TIMEOUT_SECONDS,
                write=30.0,
                pool=15.0,
            ),
        )
        if response.status_code == 402:
            raise BillingProviderError()
        if response.status_code >= 400:
            error = ProviderHTTPError(response.status_code, response.headers.get("Retry-After"))
            raise error
        try:
            body = response.json()
            return body["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise InvalidAIResponseError() from exc

    @staticmethod
    def _parse_json(raw: str) -> dict:
        text = (raw or "").strip()
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()
        try:
            result = json.loads(text)
        except json.JSONDecodeError as exc:
            raise InvalidAIResponseError() from exc
        if not isinstance(result, dict):
            raise InvalidAIResponseError()
        return result

    @staticmethod
    def _classify_failure(exc: Exception) -> tuple[str, int | None]:
        if isinstance(exc, ProviderHTTPError):
            status = exc.status_code
            retry_after = exc.retry_after
            if status == 402:
                return "billing/payment error", 300
            if status == 410:
                return "model or endpoint is no longer available (HTTP 410)", 3600
            if status == 404:
                return "model or endpoint not found (HTTP 404)", 300
            if status == 429 or status == 408 or status >= 500:
                cooldown = 60
                if retry_after:
                    try:
                        cooldown = max(1, min(3600, int(retry_after)))
                    except ValueError:
                        try:
                            date = parsedate_to_datetime(retry_after)
                            cooldown = max(1, min(3600, int((date - datetime.now(timezone.utc)).total_seconds())))
                        except (TypeError, ValueError, OverflowError):
                            pass
                return ("quota/rate limit" if status == 429 else "transient server error"), cooldown
            if status in (401, 403):
                return "invalid credentials or access denied", 300
            return f"request rejected (HTTP {status})", None
        if isinstance(exc, httpx.ConnectTimeout):
            return "connection timeout", 30
        if isinstance(exc, httpx.ReadTimeout):
            return "provider response timeout", 30
        if isinstance(exc, httpx.WriteTimeout):
            return "request write timeout", 30
        if isinstance(exc, httpx.PoolTimeout):
            return "connection pool timeout", 30
        if isinstance(exc, (httpx.TimeoutException, TimeoutError)):
            return "network timeout", 30
        if isinstance(exc, httpx.HTTPError):
            return "network error", 30
        if isinstance(exc, genai_errors.APIError):
            status = getattr(exc, "code", None) or getattr(exc, "status", None)
            if status == 402:
                return "billing/payment error", 300
            if status == 429:
                headers = getattr(getattr(exc, "response", None), "headers", {}) or {}
                retry_after = GeminiService._retry_after_seconds(headers.get("Retry-After"))
                return "quota/rate limit", retry_after or 60
            if status in (401, 403):
                return "invalid credentials or access denied", 300
            if status == 408 or (isinstance(status, int) and status >= 500):
                headers = getattr(getattr(exc, "response", None), "headers", {}) or {}
                return "transient server error", GeminiService._retry_after_seconds(headers.get("Retry-After")) or 60
            return "provider request failed", None
        return "provider request failed", None

    @staticmethod
    def _retry_after_seconds(value: str | None) -> int | None:
        if not value:
            return None
        try:
            return max(1, min(3600, int(value)))
        except ValueError:
            try:
                date = parsedate_to_datetime(value)
                return max(1, min(3600, int((date - datetime.now(timezone.utc)).total_seconds())))
            except (TypeError, ValueError, OverflowError):
                return None

    def analyze_requirements(
        self,
        document: str,
        context: str | None = None,
    ) -> dict:

        prompt = REQUIREMENT_ANALYSIS_PROMPT.format(
            document=document,
            context=context or "No additional project context was provided.",
        )

        return self._generate_json(prompt)

    @staticmethod
    def _normalize_diagram_source(source: object) -> str:
        if not isinstance(source, str):
            return ""
        source = re.sub(r"^\s*```(?:mermaid)?\s*|\s*```\s*$", "", source, flags=re.IGNORECASE)
        return source.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "  ").strip()

    @staticmethod
    def _is_diagram_url(source: object) -> bool:
        return isinstance(source, str) and bool(re.match(r"^https?://", source.strip(), flags=re.IGNORECASE))

    @classmethod
    def _recover_diagram_alias(cls, source: object, *aliases: object) -> str:
        """Prefer a real source alias over a URL accidentally stored as source."""
        normalized = cls._normalize_diagram_source(source)
        if not normalized or cls._is_diagram_url(normalized):
            for alias in aliases:
                candidate = cls._normalize_diagram_source(alias)
                if candidate and not cls._is_diagram_url(candidate):
                    return candidate
        return normalized

    @staticmethod
    def _normalize_pitch_result(result: dict) -> dict:
        """Keep the pitch response contract stable across model revisions."""
        result = result or {}
        diagrams = result.get("diagram_sources") or {}
        if not isinstance(diagrams, dict):
            diagrams = {}
        diagrams["class_diagram"] = GeminiService._recover_diagram_alias(
            diagrams.get("class_diagram"), result.get("uml_diagram"), result.get("class_diagram")
        )
        diagrams["architecture_diagram"] = GeminiService._recover_diagram_alias(
            diagrams.get("architecture_diagram"), result.get("architecture_diagram")
        )

        result["suitable_domain"] = result.get("suitable_domain") or "General software product"
        result["recommended_tech_stack"] = result.get("recommended_tech_stack") or {}
        result["diagram_sources"] = {
            name: GeminiService._recover_diagram_alias(
                diagrams.get(name),
                result.get(name),
                result.get("uml_diagram") if name == "class_diagram" else None,
            )
            for name in GeminiService.DIAGRAM_DECLARATIONS
        }
        def normalize(items, prefix):
            normalized = []
            for index, item in enumerate(items or [], 1):
                if isinstance(item, str):
                    item = {"title": f"{prefix} {index}", "description": item}
                item = dict(item)
                item.setdefault("id", f"{prefix}-{index:03d}")
                item.setdefault("origin", "generated")
                item.setdefault("acceptance_criteria", [])
                normalized.append(item)
            return normalized
        functional = normalize(result.get("functional_requirements"), "FR")
        non_functional = normalize(result.get("non_functional_requirements"), "NFR")
        normalized_cases = GeminiService._normalize_test_cases(result.get("test_cases") or [], functional + non_functional)
        result["functional_requirements"] = functional
        result["non_functional_requirements"] = non_functional
        result["test_cases"] = normalized_cases
        result.update(GeminiService._ensure_scores(result, functional, non_functional, normalized_cases))
        result["confidence_reasons"] = result.get("confidence_reasons") or []
        result["confidence_issues"] = list(result.get("confidence_issues") or [])
        result["quality_issues"] = result.get("quality_issues") or result["scoring_basis"]["issues"]
        return result

    @staticmethod
    def _normalize_test_cases(cases: list, functional: list[dict]) -> list[dict]:
        """Keep only valid requirement links and meaningful, non-duplicate cases."""
        requirements = {str(item.get("id")): item for item in functional if item.get("id")}
        normalized: list[dict] = []
        seen_ids: set[str] = set()
        seen_cases: set[tuple] = set()

        def resolve_requirement(case: dict) -> str | None:
            requested_id = str(case.get("requirement_id") or "").strip()
            if requested_id in requirements:
                return requested_id
            requirement_text = str(case.get("requirement") or "").strip().casefold()
            if not requirement_text:
                return None
            for requirement_id, requirement in requirements.items():
                title = str(requirement.get("title") or "").strip().casefold()
                description = str(requirement.get("description") or "").strip().casefold()
                identifier_present = re.search(rf"(?<![\w-]){re.escape(requirement_id.casefold())}(?![\w-])", requirement_text)
                if requirement_text in {requirement_id.casefold(), title, description} or (identifier_present and title and title in requirement_text):
                    return requirement_id
            return None

        for index, raw_case in enumerate(cases, 1):
            case = dict(raw_case) if isinstance(raw_case, dict) else {"requirement": str(raw_case)}
            case["requirement_id"] = resolve_requirement(case)
            if case["requirement_id"] is None:
                case.pop("requirement_id", None)
            steps = case.get("steps") or []
            if isinstance(steps, str):
                steps = [steps]
            case["steps"] = [str(step).strip() for step in steps if str(step).strip()]
            case["precondition"] = str(case.get("precondition") or "").strip()
            case["expected_result"] = str(case.get("expected_result") or "").strip()
            identifier = str(case.get("id") or f"TC-{index:03d}").strip()
            if not identifier or identifier in seen_ids:
                suffix = len(normalized) + 1
                identifier = f"TC-{suffix:03d}"
                while identifier in seen_ids:
                    suffix += 1
                    identifier = f"TC-{suffix:03d}"
            case["id"] = identifier
            fingerprint = (
                case.get("requirement_id") or str(case.get("requirement") or "").casefold(),
                tuple(step.casefold() for step in case["steps"]),
                case["expected_result"].casefold(),
            )
            if fingerprint in seen_cases:
                continue
            seen_cases.add(fingerprint)
            seen_ids.add(identifier)
            normalized.append(case)

        covered = {
            case.get("requirement_id") for case in normalized
            if case.get("requirement_id") in requirements
            and case["steps"] and case["expected_result"]
        }
        for requirement_id, requirement in requirements.items():
            criteria = [str(item).strip() for item in requirement.get("acceptance_criteria") or [] if str(item).strip()]
            description = str(requirement.get("description") or "").strip()
            if requirement_id in covered or not criteria or not description:
                continue
            suffix = len(normalized) + 1
            identifier = f"TC-{suffix:03d}"
            while identifier in seen_ids:
                suffix += 1
                identifier = f"TC-{suffix:03d}"
            normalized.append({
                "id": identifier,
                "requirement_id": requirement_id,
                "requirement": requirement.get("title") or requirement_id,
                "precondition": "The system and required test data are available.",
                "steps": [f"Perform the workflow described by {requirement.get('title') or requirement_id}.", "Observe the resulting system state."],
                "expected_result": criteria[0],
            })
            seen_ids.add(identifier)
        return normalized

    @classmethod
    def draft_srs_from_pitch(cls, idea: str, context: str | None = None, title: str | None = None, reason: str | None = None) -> dict:
        """Create a reviewable, explicitly labelled draft if Gemini is unavailable."""
        idea = (idea or "").strip()
        context = (context or "").strip()
        sentences = [
            re.sub(r"\s+", " ", part).strip(" -•\t")
            for part in re.split(r"(?<=[.!?])\s+|[\r\n]+", idea)
        ]
        candidates = [part for part in sentences if len(part) >= 24]
        if not candidates and idea:
            candidates = [idea]
        candidates = candidates[:12]
        project_title = title or "Software Requirements Specification"

        functional = []
        for index, candidate in enumerate(candidates, 1):
            short_title = candidate[:72].rstrip(" ,;:.!")
            functional.append({
                "id": f"FR-{index:03d}",
                "title": short_title,
                "description": f"The system shall support this capability described in the project pitch: {candidate}",
                "acceptance_criteria": [
                    "The capability is available to an authorized user through the intended workflow.",
                    "The system validates required input and provides a clear result or error message.",
                    "The resulting state is saved and can be viewed again where applicable.",
                ],
                "origin": "draft",
                "source_trace": "Project idea pitch",
            })
        if not functional:
            functional.append({
                "id": "FR-001",
                "title": "Core project workflow",
                "description": f"The system shall deliver the core workflow described by the project owner: {idea or 'Details to be confirmed.'}",
                "acceptance_criteria": ["The primary user can complete the core workflow.", "The system confirms success and reports validation errors."],
                "origin": "draft",
                "source_trace": "Project idea pitch",
            })

        tests = [{
            "id": f"TC-DRAFT-{index:03d}",
            "requirement_id": requirement["id"],
            "requirement": requirement["title"],
            "precondition": "The application is available and test data is prepared.",
            "steps": ["Complete the described workflow with valid input.", "Repeat with missing or invalid input."],
            "expected_result": "The requested workflow completes successfully for valid input and gives a clear error for invalid input.",
        } for index, requirement in enumerate(functional, 1)]
        lowered = f"{idea} {context}".casefold()
        domain = "Queue and appointment management" if any(word in lowered for word in ("queue", "wait time", "token")) else "General software product"
        result = {
            "title": f"{project_title} — Draft SRS",
            "summary": idea,
            "suitable_domain": domain,
            "recommended_tech_stack": {
                "frontend": "React with TypeScript (suggested)",
                "backend": "FastAPI or equivalent REST API (suggested)",
                "database": "PostgreSQL (suggested)",
                "infrastructure": "Cloud hosted deployment (to be confirmed)",
                "integrations": [],
            },
            "actors": ["End user", "Administrator or service operator"],
            "functional_requirements": functional,
            "non_functional_requirements": [
                {"id": "NFR-001", "category": "security", "description": "The system should authenticate users and restrict sensitive actions by role.", "acceptance_criteria": ["Unauthenticated users cannot access protected data."]},
                {"id": "NFR-002", "category": "performance", "description": "Common user actions should complete within an agreed response-time target.", "acceptance_criteria": ["The product owner defines and verifies response-time targets before release."]},
                {"id": "NFR-003", "category": "availability", "description": "The system should recover safely from service or network failures.", "acceptance_criteria": ["Users receive a clear failure message and can retry without creating duplicate actions."]},
            ],
            "user_stories": [
                {"id": "US-001", "story": "As an end user, I want to complete the core project workflow so that I can achieve the goal described in the pitch.", "acceptance_criteria": ["The workflow has clear success and error outcomes."]},
                {"id": "US-002", "story": "As an operator, I want to manage the service so that users receive consistent results.", "acceptance_criteria": ["Authorized operators can review and update service data."]},
            ],
            "assumptions": ["User roles, data retention, scale, and integrations need confirmation.", *([f"Additional context supplied: {context}"] if context else [])],
            "risks": ["The pitch does not define detailed edge cases or measurable service targets.", "Access control and privacy requirements need domain-specific review."],
            "test_cases": tests,
            "quality_score": None,
            "confidence_score": None,
            "confidence_reasons": ["Draft assembled from the submitted pitch; AI review has not completed."],
            "confidence_issues": [reason or "AI generation is temporarily unavailable. Verify and refine the draft before implementation."],
            "suggestions": ["Confirm user roles and permissions.", "Define measurable performance and availability targets.", "Review each draft requirement and add project-specific edge cases."],
            "generation_status": "draft",
            "generation_note": reason or "AI generation is temporarily unavailable. This structured draft is based on the submitted pitch and should be reviewed.",
        }
        return cls._normalize_pitch_result(result)

    def generate_test_cases(
        self,
        document: str,
    ) -> dict:

        prompt = TEST_CASE_PROMPT.format(
            document=document,
        )

        return self._generate_json(prompt)

    def check_requirement_quality(
        self,
        document: str,
    ) -> dict:

        prompt = REQUIREMENT_QUALITY_PROMPT.format(
            document=document,
        )

        return self._generate_json(prompt)

    def generate_srs_from_pitch(self, idea: str, context: str | None = None) -> dict:
        prompt = PITCH_SRS_PROMPT.format(
            idea=idea,
            context=context or "No additional project context was provided.",
        )
        try:
            result = self._normalize_pitch_result(
                self._generate_json(prompt, preferred_provider="ollama")
            )
            repair = self.repair_diagram_sources(result)
            result["diagram_sources"] = repair["diagram_sources"]
            if repair["failures"]:
                result["generation_status"] = "draft"
                result["generation_note"] = (
                    "Some diagrams could not be generated: "
                    + "; ".join(f"{name}: {reason}" for name, reason in repair["failures"].items())
                )
                result["diagram_generation_issues"] = repair["failures"]
            return result
        except AIProviderUnavailableError as exc:
            logger.warning("Pitch SRS generation failed; returning a labelled draft: %s", exc.public_summary)
            return self.draft_srs_from_pitch(
                idea,
                context,
                reason=f"{exc.public_summary} Review this structured pitch-based draft and retry when a provider is available.",
            )

    def generate_clarification_questions(self, document: str, context: str | None = None) -> dict:
        return self._generate_json(CLARIFICATION_QUESTIONS_PROMPT.format(
            document=document,
            context=context or "No additional project context was provided.",
        ))

    @staticmethod
    def _default_diagrams() -> dict[str, str]:
        return {
            "class_diagram": "classDiagram\n  class Requirement\n  class User\n  User --> Requirement : defines",
            "er_diagram": "erDiagram\n  PROJECT ||--o{ REQUIREMENT : contains\n  REQUIREMENT ||--o{ TEST_CASE : verifies",
            "architecture_diagram": "flowchart LR\n  User --> UI --> API --> AI\n  API --> Database",
            "use_case_diagram": "usecase-beta\nactor Stakeholder\nsystemBoundary System\n  UC1(\"Analyze SRS\")\n  UC2(\"Improve SRS\")\nend\nStakeholder --> UC1\nStakeholder --> UC2",
            "data_flow_diagram": "flowchart LR\n  Source[Uploaded document] --> Extract --> Analyze --> ImprovedSRS",
            "sequence_diagram": "sequenceDiagram\n  actor User\n  User->>UI: Upload SRS\n  UI->>API: Analyze source\n  API-->>UI: Normalized result",
        }

    DIAGRAM_DECLARATIONS = {
        "class_diagram": ("classDiagram",),
        "er_diagram": ("erDiagram",),
        "architecture_diagram": ("flowchart", "graph"),
        "use_case_diagram": ("usecase-beta",),
        "data_flow_diagram": ("flowchart", "graph"),
        "sequence_diagram": ("sequenceDiagram",),
    }

    @classmethod
    def validate_diagram_source(cls, diagram_type: str, source: object) -> tuple[bool, str | None]:
        if diagram_type not in cls.DIAGRAM_DECLARATIONS:
            return False, "Unsupported diagram type."
        normalized = cls._normalize_diagram_source(source)
        if not normalized:
            return False, "Mermaid source is missing."
        if cls._is_diagram_url(normalized):
            return False, "The saved value is a URL, not Mermaid source."
        declaration = normalized.splitlines()[0].split(maxsplit=1)[0]
        if declaration not in cls.DIAGRAM_DECLARATIONS[diagram_type]:
            return False, f"Expected {', '.join(cls.DIAGRAM_DECLARATIONS[diagram_type])}; found {declaration}."
        if len(normalized.splitlines()) < 2:
            return False, "The diagram contains no Mermaid statements."
        return True, None

    @classmethod
    def repair_diagram_sources(cls, result: dict) -> dict:
        """Regenerate only invalid diagrams; preserve all other SRS fields and sources."""
        sources = result.get("diagram_sources")
        if not isinstance(sources, dict):
            sources = {}
        sources = dict(sources)
        failures: dict[str, str] = {}
        repaired: list[str] = []
        for diagram_type, declarations in cls.DIAGRAM_DECLARATIONS.items():
            valid, reason = cls.validate_diagram_source(diagram_type, sources.get(diagram_type))
            if valid:
                continue
            prompt = (
                "Return JSON only with one key named source containing actual Mermaid code. "
                f"Generate a project-specific {diagram_type} using declaration {declarations[0]}. "
                "Do not return a URL, markdown fence, or explanation. Preserve relevant entities and relationships.\n"
                f"Project title: {result.get('title') or 'Software system'}\n"
                f"Summary: {result.get('summary') or ''}\n"
                f"Actors: {json.dumps(result.get('actors') or [])}\n"
                f"Functional requirements: {json.dumps(result.get('functional_requirements') or [])}\n"
                f"Non-functional requirements: {json.dumps(result.get('non_functional_requirements') or [])}"
            )
            try:
                generated = cls()._generate_json(prompt, preferred_provider="ollama", local_only=True)
                candidate = cls._normalize_diagram_source(generated.get("source"))
                valid, generated_reason = cls.validate_diagram_source(diagram_type, candidate)
                if valid:
                    sources[diagram_type] = candidate
                    repaired.append(diagram_type)
                else:
                    failures[diagram_type] = f"Generated source is invalid: {generated_reason}"
            except AIProviderUnavailableError as exc:
                failures[diagram_type] = exc.public_summary
            except Exception as exc:
                logger.warning("Diagram generation failed type=%s exception_type=%s", diagram_type, type(exc).__name__)
                failures[diagram_type] = f"Diagram generation failed ({type(exc).__name__})."
            if not valid and diagram_type not in failures:
                failures[diagram_type] = reason or "Invalid Mermaid source."
        return {"diagram_sources": sources, "failures": failures, "repaired": repaired}

    @staticmethod
    def _ensure_scores(
        quality: dict | None,
        functional: list[dict],
        non_functional: list[dict],
        test_cases: list[dict],
    ) -> dict:
        """Score observable specification completeness; leave analysis confidence unevaluated.

        The percentage is a structural checklist, not a semantic judgment. A
        model-supplied confidence number cannot establish correctness without
        independent validation, so it is deliberately not treated as evidence.
        """
        quality = dict(quality or {})
        if quality.get("scoring_available") is False or quality.get("generation_status") == "draft":
            quality["quality_score"] = None
            quality["confidence_score"] = None
            quality["scoring_basis"] = {
                "method": "not_evaluated",
                "issues": ["Analysis was incomplete; scoring was not performed."],
            }
            quality.pop("scoring_available", None)
            return quality

        requirements = [*functional, *non_functional]
        ids = [str(item.get("id") or "").strip() for item in requirements]
        unique_ids = {value for value in ids if value}
        duplicate_ids = {value for value in unique_ids if ids.count(value) > 1}
        valid_functional_ids = {str(item.get("id")) for item in functional if item.get("id")}
        covered_ids = {
            case.get("requirement_id") for case in test_cases
            if case.get("requirement_id") in valid_functional_ids
            and case.get("steps") and case.get("expected_result")
        }
        issues: list[str] = []
        passed = 0
        total = 0
        for index, item in enumerate(requirements, 1):
            identifier = str(item.get("id") or f"Requirement {index}")
            checks = {
                "unique identifier": bool(item.get("id")) and identifier not in duplicate_ids,
                "description": bool(str(item.get("description") or "").strip()),
                "acceptance criteria": bool(item.get("acceptance_criteria")),
                "source trace": bool(str(item.get("source_trace") or "").strip()),
            }
            if item in functional:
                checks["meaningful linked test case"] = identifier in covered_ids
            for label, ok in checks.items():
                total += 1
                passed += int(ok)
                if not ok:
                    issues.append(f"{identifier} is missing a {label}.")
        quality["quality_score"] = round(100 * passed / total) if total else None
        quality["confidence_score"] = None
        quality["scoring_basis"] = {
            "method": "requirements completeness checklist",
            "checks_passed": passed,
            "checks_total": total,
            "meaningfully_covered_functional_requirements": len(covered_ids),
            "functional_requirement_count": len(valid_functional_ids),
            "issues": issues,
        }
        quality["issues"] = [*(quality.get("issues") or []), *issues]
        confidence_reasons = list(quality.get("confidence_reasons") or [])
        confidence_reasons.append("Analysis confidence was not independently validated, so no confidence score is reported.")
        quality["confidence_reasons"] = confidence_reasons
        return quality

    @classmethod
    def normalize_upload_result(cls, *, source_text: str, analysis: dict, test_cases: dict, quality: dict, refactored: dict | None = None, questions: dict | None = None) -> dict:
        """Normalize model drift into the stable Mode 2 contract used by the UI."""
        analysis = analysis or {}
        refactored = refactored or {}
        analysis_diagrams = analysis.get("diagram_sources") if isinstance(analysis.get("diagram_sources"), dict) else {}
        refactored_diagrams = refactored.get("diagram_sources") if isinstance(refactored.get("diagram_sources"), dict) else {}
        merged_diagrams = {**cls._default_diagrams(), **analysis_diagrams, **refactored_diagrams}
        for name, aliases in {
            "class_diagram": (refactored.get("uml_diagram"), analysis.get("uml_diagram")),
            "architecture_diagram": (refactored.get("architecture_diagram"), analysis.get("architecture_diagram")),
        }.items():
            merged_diagrams[name] = cls._recover_diagram_alias(merged_diagrams.get(name), *aliases)
        diagrams = {name: cls._normalize_diagram_source(source) for name, source in merged_diagrams.items()}
        functional = refactored.get("functional_requirements") or []
        non_functional = refactored.get("non_functional_requirements") or []

        def normalize_items(items, prefix, default_origin=None):
            normalized = []
            for index, item in enumerate(items, 1):
                if isinstance(item, str):
                    item = {"title": f"{prefix} {index}", "description": item}
                item = dict(item)
                item.setdefault("id", f"{prefix}-{index:03d}")
                item.setdefault("origin", default_origin or ("extracted" if item.get("source_trace") else "improved"))
                item.setdefault("acceptance_criteria", [])
                normalized.append(item)
            return normalized

        functional = normalize_items(functional, "FR")
        non_functional = normalize_items(non_functional, "NFR")
        def preserve_extracted(refactored_items, extracted_items, prefix):
            extracted = normalize_items(extracted_items or [], prefix, "extracted")
            combined = list(refactored_items)
            by_id = {item.get("id"): item for item in combined}
            descriptions = {str(item.get("description", "")).strip().casefold() for item in combined}
            for item in extracted:
                if item.get("id") in by_id:
                    if not by_id[item.get("id")].get("source_trace"):
                        by_id[item.get("id")]["source_trace"] = item.get("source_trace")
                    continue
                if str(item.get("description", "")).strip().casefold() in descriptions:
                    continue
                combined.append(item)
            return combined
        functional = preserve_extracted(functional, analysis.get("functional_requirements"), "FR")
        non_functional = preserve_extracted(non_functional, analysis.get("non_functional_requirements"), "NFR")
        users = normalize_items(refactored.get("user_stories") or analysis.get("user_stories") or [], "US")
        cases = test_cases.get("test_cases") if isinstance(test_cases, dict) else test_cases
        normalized_cases = cls._normalize_test_cases(cases or [], functional + non_functional)
        issues = quality.get("issues") or []
        missing = analysis.get("missing_requirements") or refactored.get("missing_requirements") or quality.get("missing_requirements") or []
        additions = refactored.get("suggested_additions") or analysis.get("suggested_additions") or quality.get("suggested_additions") or []
        change_summary = refactored.get("change_summary") or {
            "added": additions,
            "improved": quality.get("improved_requirements", []),
            "unchanged": [],
            "removed": [],
        }
        quality = cls._ensure_scores(quality, functional, non_functional, normalized_cases)
        return {
            "is_software_document": analysis.get("is_software_document", True),
            "title": refactored.get("title") or analysis.get("title") or "Improved Software Requirements Specification",
            "summary": refactored.get("summary") or analysis.get("summary") or "",
            "document_name": analysis.get("document_name"),
            "source_text": source_text,
            "source_text_length": len(source_text),
            "analysis": {**analysis, "functional_requirements": functional, "non_functional_requirements": non_functional, "user_stories": users, "diagram_sources": diagrams, "missing_requirements": missing, "suggested_additions": additions},
            "functional_requirements": functional,
            "non_functional_requirements": non_functional,
            "user_stories": users,
            "acceptance_criteria": [criterion for item in functional + non_functional + users for criterion in item.get("acceptance_criteria", [])],
            "suitable_domain": refactored.get("suitable_domain") or analysis.get("suitable_domain") or "General software product",
            "recommended_tech_stack": refactored.get("recommended_tech_stack") or analysis.get("recommended_tech_stack") or {},
            "actors": refactored.get("actors") or analysis.get("actors") or [],
            "assumptions": refactored.get("assumptions") or analysis.get("assumptions") or [],
            "risks": refactored.get("risks") or analysis.get("risks") or [],
            "missing_requirements": missing,
            "suggested_additions": additions,
            "test_cases": normalized_cases,
            "missing_test_cases": [],
            "quality": quality,
            "quality_score": quality.get("quality_score"),
            "confidence_score": quality.get("confidence_score"),
            "confidence_reasons": quality.get("confidence_reasons") or [],
            "refactored_srs": refactored,
            "clarification_questions": (questions or {}).get("questions", []),
            "diagram_sources": diagrams,
            "change_summary": change_summary,
        }

    @classmethod
    def draft_upload_result(cls, *, source_text: str, document_name: str | None, reason: str) -> dict:
        """Build a source-preserving Mode 2 draft when the AI provider is unavailable."""
        functional: list[dict] = []
        non_functional: list[dict] = []
        user_stories: list[dict] = []
        seen: set[str] = set()
        requirement_pattern = re.compile(r"\b(?:shall|must|required to|needs to|should|will|is able to|can)\b", re.IGNORECASE)
        explicit_id_pattern = re.compile(r"\b((?:FR|NFR|REQ|SRS)[-_ ]?\d+(?:\.\d+)*)\b", re.IGNORECASE)
        nfr_pattern = re.compile(r"\b(performance|security|availability|reliability|usability|accessibility|maintainability|scalability|privacy|response time|backup|retention)\b", re.IGNORECASE)

        for line_number, line in enumerate(source_text.splitlines(), 1):
            candidates = line.split("|") if "|" in line else [line]
            for raw_candidate in candidates:
                candidate = re.sub(r"^\s*(?:[-*•]+|\d+(?:\.\d+)*[.)]?|\[[ xX]\])\s*", "", raw_candidate).strip()
                if not candidate:
                    continue
                story_match = re.search(r"\bAs an?\s+[^,]+,\s*I want\s+.+", candidate, re.IGNORECASE)
                if story_match:
                    story = story_match.group(0)
                    user_stories.append({"id": f"US-{len(user_stories) + 1:03d}", "story": story, "origin": "extracted", "source_trace": f"Source line {line_number}"})
                if not explicit_id_pattern.search(candidate) and not requirement_pattern.search(candidate):
                    continue
                normalized_text = candidate.casefold()
                if normalized_text in seen:
                    continue
                seen.add(normalized_text)
                explicit_id = explicit_id_pattern.search(candidate)
                is_nfr = bool(nfr_pattern.search(candidate)) or bool(explicit_id and explicit_id.group(1).upper().startswith("NFR"))
                target = non_functional if is_nfr else functional
                prefix = "NFR" if is_nfr else "FR"
                assigned_id = explicit_id.group(1).upper().replace(" ", "-") if explicit_id else f"{prefix}-{len(target) + 1:03d}"
                target.append({
                    "id": assigned_id,
                    "title": candidate[:100].rstrip(" ,;:."),
                    "description": candidate,
                    "category": "quality attribute" if is_nfr else None,
                    "acceptance_criteria": [f"Verify the documented behavior: {candidate}"],
                    "origin": "extracted",
                    "source_trace": f"Source line {line_number}",
                })

        if not functional and not non_functional:
            functional.append({
                "id": "FR-001",
                "title": "Review extracted software requirements",
                "description": "The source document was preserved in full. The deterministic fallback could not identify requirement statements; review the source text and retry AI analysis.",
                "acceptance_criteria": ["A reviewer confirms and records each functional requirement from the source document."],
                "origin": "draft",
                "source_trace": "Generated from the uploaded document because AI analysis was unavailable.",
            })

        lowered = source_text.casefold()
        domain = "Library management" if "librar" in lowered else "Healthcare" if any(word in lowered for word in ("patient", "hospital", "clinic")) else "Education" if any(word in lowered for word in ("student", "school", "college", "course")) else "General software product"
        suggestions = [
            "Confirm user roles, permissions, and administrative workflows.",
            "Specify measurable performance, availability, and data-retention targets.",
            "Define validation, failure recovery, privacy, and audit requirements.",
        ]
        analysis = {
            "title": document_name or "Improved Software Requirements Specification",
            "summary": "The original document text is preserved. Requirement statements below were identified with a deterministic source scan while AI analysis is unavailable.",
            "suitable_domain": domain,
            "recommended_tech_stack": {"status": "Suggested for review", "frontend": "To be confirmed", "backend": "To be confirmed", "database": "To be confirmed"},
            "functional_requirements": functional,
            "non_functional_requirements": non_functional,
            "user_stories": user_stories,
            "actors": [],
            "risks": ["AI analysis was unavailable; extracted statements have not been semantically verified."],
            "assumptions": ["Technology and domain recommendations require project-owner confirmation."],
            "suggested_additions": suggestions,
            "missing_requirements": [],
        }
        test_cases = {"test_cases": [{
            "id": f"TC-DRAFT-{index:03d}",
            "requirement_id": requirement["id"],
            "requirement": requirement["title"],
            "precondition": "The system and required test data are available.",
            "steps": requirement["acceptance_criteria"],
            "expected_result": f"The system satisfies the extracted requirement: {requirement['description']}",
        } for index, requirement in enumerate(functional, 1)]}
        quality = {
            "quality_score": None,
            "confidence_score": None,
            "scoring_available": False,
            "confidence_reasons": ["The full source text is preserved and candidate requirement statements include source line references."],
            "issues": [{"severity": "review", "reason": "AI quality scoring could not run. Review the extracted requirements before relying on the draft."}],
        }
        questions = {"questions": [
            {"id": "Q-001", "question": "Which user roles may create, update, approve, or delete records?", "reason": "The role and permission model affects requirements and architecture.", "priority": "high"},
            {"id": "Q-002", "question": "What measurable performance and availability targets must the system meet?", "reason": "Numeric targets make non-functional requirements testable.", "priority": "medium"},
            {"id": "Q-003", "question": "What should happen when required data is missing or a dependent service is unavailable?", "reason": "Failure behavior needs explicit recovery requirements.", "priority": "medium"},
        ]}
        report = cls.normalize_upload_result(
            source_text=source_text,
            analysis=analysis,
            test_cases=test_cases,
            quality=quality,
            refactored={"title": analysis["title"], "summary": analysis["summary"], "functional_requirements": functional, "non_functional_requirements": non_functional, "user_stories": user_stories, "suggested_additions": suggestions},
            questions=questions,
        )
        report["document_name"] = document_name
        report["generation_status"] = "draft"
        report["generation_note"] = reason
        report["analysis"]["generation_status"] = "draft"
        return report

    def refactor_srs(
        self,
        document: str,
        answers: Mapping[str, str] | None = None,
        context: str | None = None,
    ) -> dict:
        """Refactor a document, optionally applying user clarification answers.

        ``answers`` is optional so the original one-argument refactor flow remains
        compatible.  Serializing a copied mapping also keeps prompt construction
        deterministic and prevents callers' dictionaries from being mutated.
        """
        clarification_answers = json.dumps(
            dict(answers) if answers else {},
            ensure_ascii=False,
            indent=2,
        )
        prompt = REFACTOR_SRS_PROMPT.format(
            document=document,
            answers=clarification_answers,
            context=context or "No additional project context was provided.",
        )
        return self._generate_json(prompt)
