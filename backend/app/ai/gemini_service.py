from __future__ import annotations

from asyncio.log import logger
from email.mime import text
import json

from google import genai

from app.ai.prompts import (
    REQUIREMENT_ANALYSIS_PROMPT,
    TEST_CASE_PROMPT,
    REQUIREMENT_QUALITY_PROMPT,
)
from app.core.config import settings


class GeminiService:
    MODEL_NAME = "gemini-2.5-flash"

    def __init__(self):
        self.client = genai.Client(
            api_key=settings.gemini_api_key,
        )

    def test_connection(self) -> str:
        response = self.client.models.generate_content(
            model=self.MODEL_NAME,
            contents="Reply with exactly: SpecMind AI connected successfully.",
        )

        return response.text.strip()

    def _generate_json(self, prompt: str) -> dict:
        """
        Sends a prompt to Gemini and returns the parsed JSON response.
        """

        from google.genai import types

        response = self.client.models.generate_content(
            model=self.MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )

        text = response.text.strip()

        if text.startswith("```json"):
            text = text.replace("```json", "", 1)

        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        try:
         return json.loads(text)
        except json.JSONDecodeError as e:
                logger.error("Invalid JSON returned by Gemini")
                logger.error(text)
                raise ValueError("Gemini returned invalid JSON.") from e

    def analyze_requirements(
        self,
        document: str,
    ) -> dict:

        prompt = REQUIREMENT_ANALYSIS_PROMPT.format(
            document=document,
        )

        return self._generate_json(prompt)

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