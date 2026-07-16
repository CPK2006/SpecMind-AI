from __future__ import annotations
from email.mime import text
import json

from click import prompt
from google import genai

from app.core.config import settings
from app.ai.prompts import REQUIREMENT_ANALYSIS_PROMPT


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