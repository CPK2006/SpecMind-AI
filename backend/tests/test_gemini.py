import json

from app.ai.gemini_service import GeminiService


service = GeminiService()

document = """
The system shall allow users to login.

The system shall generate reports.

The response time shall be less than 2 seconds.

The application shall encrypt passwords.
"""

result = service.analyze_requirements(document)

print(json.dumps(result, indent=4))