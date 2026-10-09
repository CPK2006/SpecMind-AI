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

    def _generate_json(self, prompt: str) -> dict:
        """
        Sends a prompt to Gemini and returns the parsed JSON response.
        """

        failures: list[str] = []
        providers = self._configured_providers()
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
    def _configured_providers(cls) -> list[tuple[str, str, str]]:
        providers = []
        if settings.nvidia_api_key.strip():
            providers.append(("nvidia", settings.nvidia_model, settings.nvidia_api_key.strip()))
        if settings.openrouter_api_key.strip():
            providers.append(("openrouter", settings.openrouter_model, settings.openrouter_api_key.strip()))
        raw_keys = [*settings.gemini_api_keys.split(","), settings.gemini_api_key]
        keys = list(dict.fromkeys(key.strip() for key in raw_keys if key.strip()))
        if keys:
            with cls._gemini_lock:
                start = cls._gemini_next_key % len(keys)
                cls._gemini_next_key += 1
            rotated = keys[start:] + keys[:start]
            providers.extend(("gemini", cls.MODEL_NAME, key) for key in rotated)
        return providers

    @staticmethod
    def _request_provider(provider: str, model: str, key: str, prompt: str) -> str:
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
    def _normalize_pitch_result(result: dict) -> dict:
        """Keep the pitch response contract stable across model revisions."""
        result = result or {}
        diagrams = result.get("diagram_sources") or {}
        if result.get("uml_diagram") and not diagrams.get("class_diagram"):
            diagrams["class_diagram"] = result["uml_diagram"]
        if result.get("architecture_diagram") and not diagrams.get("architecture_diagram"):
            diagrams["architecture_diagram"] = result["architecture_diagram"]

        result["suitable_domain"] = result.get("suitable_domain") or "General software product"
        result["recommended_tech_stack"] = result.get("recommended_tech_stack") or {}
        result["diagram_sources"] = {
            "class_diagram": diagrams.get("class_diagram", "classDiagram\n  class Product"),
            "er_diagram": diagrams.get("er_diagram", "erDiagram\n  PRODUCT ||--o{ USER : serves"),
            "architecture_diagram": diagrams.get("architecture_diagram", "flowchart LR\n  Client --> API --> Database"),
            "use_case_diagram": diagrams.get("use_case_diagram", "flowchart LR\n  Actor[User] --> UseCase((Use case))"),
            "data_flow_diagram": diagrams.get("data_flow_diagram", "flowchart LR\n  Input --> Process --> Output"),
            "sequence_diagram": diagrams.get("sequence_diagram", "sequenceDiagram\n  actor User\n  User->>System: Start workflow"),
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
        cases = result.get("test_cases") or []
        normalized_cases = []
        covered = set()
        for index, case in enumerate(cases, 1):
            case = dict(case) if isinstance(case, dict) else {"expected_result": str(case)}
            requirement_id = case.get("requirement_id")
            if not requirement_id:
                requirement = str(case.get("requirement") or "")
                requirement_id = next((item["id"] for item in functional if item["id"].casefold() in requirement.casefold()), None)
            if not requirement_id and functional:
                requirement_id = functional[0]["id"]
            case["requirement_id"] = requirement_id or "UNMAPPED"
            case.setdefault("id", f"TC-{index:03d}")
            normalized_cases.append(case)
            covered.add(case["requirement_id"])
        for item in functional:
            if item["id"] not in covered:
                normalized_cases.append({
                    "id": f"TC-AUTO-{len(normalized_cases) + 1:03d}",
                    "requirement_id": item["id"],
                    "requirement": item.get("title") or item.get("description") or item["id"],
                    "precondition": "The system is available and required test data is prepared.",
                    "steps": item.get("acceptance_criteria") or [f"Execute the behavior described by {item['id']}"],
                    "expected_result": item.get("description") or f"The system satisfies {item['id']}.",
                    "coverage_gap_filled": True,
                })
        result["functional_requirements"] = functional
        result["non_functional_requirements"] = non_functional
        result["test_cases"] = normalized_cases
        result.update(GeminiService._ensure_scores(
            result,
            functional,
            non_functional,
            normalized_cases,
        ))
        result["confidence_reasons"] = result.get("confidence_reasons") or []
        result["confidence_issues"] = result.get("confidence_issues") or []
        return result

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
            return self._normalize_pitch_result(self._generate_json(prompt))
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
            "use_case_diagram": "flowchart LR\n  Actor[Stakeholder] --> Analyze((Analyze SRS))\n  Actor --> Improve((Improve SRS))",
            "data_flow_diagram": "flowchart LR\n  Source[Uploaded document] --> Extract --> Analyze --> ImprovedSRS",
            "sequence_diagram": "sequenceDiagram\n  actor User\n  User->>UI: Upload SRS\n  UI->>API: Analyze source\n  API-->>UI: Normalized result",
        }

    @staticmethod
    def _ensure_scores(
        quality: dict | None,
        functional: list[dict],
        non_functional: list[dict],
        test_cases: list[dict],
    ) -> dict:
        """Fill missing report scores without replacing provider-generated scores.

        Drafts are still useful when an AI provider is unavailable, so their
        report must not display blank scores. This deterministic rubric measures
        observable structure and test coverage, not semantic quality.
        """
        quality = dict(quality or {})
        requirements = [*functional, *non_functional]
        if requirements:
            complete = sum(
                sum(bool(item.get(field)) for field in ("title", "category", "description"))
                + bool(item.get("acceptance_criteria"))
                for item in requirements
            )
            completeness = complete / (len(requirements) * 4)
        else:
            completeness = 0.0

        functional_ids = {item.get("id") for item in functional if item.get("id")}
        covered_ids = {
            item.get("requirement_id")
            for item in test_cases
            if item.get("requirement_id") in functional_ids
        }
        coverage = len(covered_ids) / len(functional_ids) if functional_ids else 0.0
        fallback_quality = round(100 * (0.65 * completeness + 0.35 * coverage))
        # These values do not include semantic AI validation, so confidence is
        # intentionally capped below full certainty.
        fallback_confidence = round(45 + 40 * (0.5 * completeness + 0.5 * coverage))

        if quality.get("quality_score") is None:
            quality["quality_score"] = fallback_quality
        if quality.get("confidence_score") is None:
            quality["confidence_score"] = fallback_confidence
        return quality

    @classmethod
    def normalize_upload_result(cls, *, source_text: str, analysis: dict, test_cases: dict, quality: dict, refactored: dict | None = None, questions: dict | None = None) -> dict:
        """Normalize model drift into the stable Mode 2 contract used by the UI."""
        analysis = analysis or {}
        refactored = refactored or {}
        diagrams = {**cls._default_diagrams(), **(analysis.get("diagram_sources") or {}), **(refactored.get("diagram_sources") or {})}
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
        normalized_cases = []
        for index, item in enumerate(cases or [], 1):
            item = dict(item) if isinstance(item, dict) else {"expected_result": str(item)}
            requirement_id = item.get("requirement_id")
            if not requirement_id:
                requirement_text = str(item.get("requirement") or "")
                requirement_id = next((req.get("id") for req in functional if req.get("id", "").casefold() in requirement_text.casefold()), None)
            if not requirement_id and functional:
                requirement_id = functional[0].get("id")
            item["requirement_id"] = requirement_id or "UNMAPPED"
            item.setdefault("id", f"TC-{index:03d}")
            normalized_cases.append(item)
        covered_requirements = {case.get("requirement_id") for case in normalized_cases}
        for requirement in functional:
            requirement_id = requirement.get("id")
            if requirement_id and requirement_id not in covered_requirements:
                criteria = requirement.get("acceptance_criteria") or []
                normalized_cases.append({
                    "id": f"TC-AUTO-{len(normalized_cases) + 1:03d}",
                    "requirement_id": requirement_id,
                    "requirement": requirement.get("title") or requirement.get("description") or requirement_id,
                    "precondition": "The system is available and the required user or test data is prepared.",
                    "steps": [str(criterion) for criterion in criteria] or [f"Execute the behavior described by {requirement_id}."],
                    "expected_result": requirement.get("description") or f"The system satisfies {requirement_id}.",
                    "coverage_gap_filled": True,
                })
                covered_requirements.add(requirement_id)
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
            "quality": {**quality, "issues": issues, "quality_score": quality.get("quality_score", 0), "confidence_score": quality.get("confidence_score", 0)},
            "quality_score": quality.get("quality_score", 0),
            "confidence_score": quality.get("confidence_score", 0),
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
