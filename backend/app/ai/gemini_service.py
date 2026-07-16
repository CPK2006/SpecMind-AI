from __future__ import annotations

import json

from google import genai

from app.ai.prompts import (
    REQUIREMENT_ANALYSIS_PROMPT,
    TEST_CASE_PROMPT,
)
from app.core.config import settings


class GeminiService:

    def __init__(self):
        self.client = genai.Client(
            api_key=settings.gemini_api_key,
        )

    def test_connection(self) -> str:
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Reply with exactly: SpecMind AI connected successfully.",
        )

        return response.text.strip()

    def analyze_requirements(
        self,
        document: str,
    ) -> dict:

        prompt = REQUIREMENT_ANALYSIS_PROMPT.format(
            document=document,
        )

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        text = response.text.strip()

        if text.startswith("```json"):
            text = text.replace("```json", "", 1)

        if text.endswith("```"):
            text = text[:-3]

        return json.loads(text.strip())

    def generate_test_cases(
        self,
        document: str,
    ) -> dict:

        prompt = TEST_CASE_PROMPT.format(
            document=document,
        )

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        text = response.text.strip()

        if text.startswith("```json"):
            text = text.replace("```json", "", 1)

        if text.endswith("```"):
            text = text[:-3]

        return json.loads(text.strip())