REQUIREMENT_ANALYSIS_PROMPT = """
You are a Senior Software Requirements Engineer.

Your task is to analyze ONLY software requirement documents.

If the uploaded document is NOT related to software development,
return exactly this JSON:

{{
  "is_software_document": false,
  "message": "Unsupported document type."
}}

Otherwise return ONLY valid JSON.

Required format:

{{
  "is_software_document": true,

  "functional_requirements": [],

  "non_functional_requirements": [],

  "actors": [],

  "user_stories": [],

  "assumptions": [],

  "risks": []
}}

Document:

{document}
"""


USER_STORY_PROMPT = """
You are a Senior Business Analyst.

Generate user stories from the following software requirements.

Return ONLY valid JSON.

Required format:

{{
  "user_stories": [
    {{
      "title": "User Login",
      "story": "As a user, I want to log in so that I can access my account."
    }}
  ]
}}

Document:

{document}
"""
TEST_CASE_PROMPT = """
You are a Senior QA Engineer.

Generate software test cases from the following Software Requirements Specification.

Return ONLY valid JSON.

Required format:

{{
  "test_cases": [
    {{
      "id": "TC-001",
      "requirement": "...",
      "precondition": "...",
      "steps": [
        "...",
        "..."
      ],
      "expected_result": "..."
    }}
  ]
}}

Document:

{document}
"""