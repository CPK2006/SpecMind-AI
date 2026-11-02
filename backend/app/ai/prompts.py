REQUIREMENT_ANALYSIS_PROMPT = """
You are a Senior Software Requirements Engineer.

Your task is to analyze ONLY software requirement documents.

If the uploaded document is NOT related to software development,
return exactly this JSON:

{{
  "is_software_document": false,
  "message": "Unsupported document type."
}}

Otherwise return ONLY valid JSON. Extract every requirement present in the source;
do not summarize or omit items. Preserve section, page, or short-quote source
references where possible. Distinguish source content from suggestions.

Required format:

{{
  "is_software_document": true,

  "summary": "...",
  "suitable_domain": "...",
  "recommended_tech_stack": {{"frontend": "...", "backend": "...", "database": "...", "infrastructure": "...", "integrations": []}},
  "functional_requirements": [{{"id": "FR-001", "title": "...", "description": "...", "acceptance_criteria": [], "origin": "extracted", "source_trace": "section or page reference"}}],
  "non_functional_requirements": [{{"id": "NFR-001", "category": "...", "description": "...", "acceptance_criteria": [], "origin": "extracted", "source_trace": "..."}}],
  "actors": [],
  "user_stories": [{{"id": "US-001", "story": "...", "acceptance_criteria": [], "source_trace": "..."}}],
  "assumptions": [],
  "risks": [],
  "missing_requirements": [],
  "suggested_additions": [],
  "diagram_sources": {{"class_diagram": "...", "er_diagram": "...", "architecture_diagram": "...", "use_case_diagram": "...", "data_flow_diagram": "...", "sequence_diagram": "..."}}
}}

Document:

{document}

Additional user-provided project context (context only; not extracted source):
{context}
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
      "requirement_id": "FR-001",
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
REQUIREMENT_QUALITY_PROMPT = """
You are a Senior Requirements Engineer.

Review the following software requirements.

Identify:

- Ambiguous wording
- Missing information
- Non-measurable statements
- Conflicting requirements
- Weak wording

Return ONLY valid JSON.

Required format:

{{
  "quality_score": 0,
  "confidence_score": 0,
  "confidence_reasons": [],
  "issues": [
    {{
      "requirement": "...",
      "type": "...",
      "severity": "...",
      "reason": "...",
      "suggestion": "..."
    }}
  ],
  "improved_requirements": [
    "..."
  ]
}}

Document:

{document}
"""

PITCH_SRS_PROMPT = """
You are a principal software architect and requirements analyst.

Turn the following project idea into a reviewable software requirements
specification. Treat only behavior explicitly stated in the pitch as confirmed
functionality. Put inferred capabilities in suggestions or assumptions; do not
present authentication, password recovery, external integrations, technology
choices, or numeric service targets as confirmed requirements unless the pitch
states them. Do not duplicate requirements or add filler test cases. Give each
functional requirement an ID, source trace to the relevant pitch phrase, and
observable acceptance criteria. Link test cases only to IDs in the returned
functional requirements, and include meaningful ordered steps and observable
expected results. Return ONLY valid JSON with this exact top-level shape.
Use Mermaid syntax appropriate to each diagram: classDiagram, erDiagram,
flowchart for architecture/data-flow, usecase-beta for a use-case diagram, and
sequenceDiagram. Keep diagram labels concise and escape them as Mermaid requires.

{{
  "title": "...",
  "suitable_domain": "...",
  "recommended_tech_stack": {{
    "frontend": "...",
    "backend": "...",
    "database": "...",
    "infrastructure": "...",
    "integrations": []
  }},
  "summary": "...",
  "actors": [],
  "functional_requirements": [
    {{"id": "FR-001", "title": "...", "description": "...", "acceptance_criteria": [], "origin": "improved", "source_trace": "..."}}
  ],
  "non_functional_requirements": [
    {{"id": "NFR-001", "category": "performance", "description": "...", "acceptance_criteria": [], "origin": "improved", "source_trace": "..."}}
  ],
  "user_stories": [{{"id": "US-001", "story": "...", "acceptance_criteria": []}}],
  "assumptions": [],
  "risks": [],
  "test_cases": [{{"id": "TC-001", "requirement_id": "FR-001", "precondition": "...", "steps": [], "expected_result": "..."}}],
  "diagram_sources": {{
    "class_diagram": "mermaid source",
    "er_diagram": "mermaid source",
    "architecture_diagram": "mermaid source",
    "use_case_diagram": "mermaid source",
    "data_flow_diagram": "mermaid source",
    "sequence_diagram": "mermaid source"
  }},
  "quality_score": 0,
  "confidence_score": 0,
  "confidence_reasons": [],
  "confidence_issues": [],
  "suggestions": []
}}

Project context:
{context}

Idea:
{idea}
"""

CLARIFICATION_QUESTIONS_PROMPT = """
You are a senior business analyst reviewing a software requirements document.
Return ONLY valid JSON in this shape:
{{
  "questions": [
    {{"id": "Q-001", "question": "...", "reason": "...", "priority": "high"}}
  ]
}}

Ask only questions whose answers could materially change requirements, acceptance
criteria, security, data, integrations, or architecture. Ask no more than 8.

Document:
{document}

Project context that may clarify the intended product:
{context}
"""

REFACTOR_SRS_PROMPT = """
You are a principal requirements engineer. Refactor the source document into a
clear, complete, implementation-ready SRS. Preserve the original intent, remove
ambiguity, add measurable acceptance criteria, assign stable IDs, and explicitly
mark assumptions instead of inventing facts. Clearly separate source-derived
content from AI suggestions using `origin` values of `extracted`, `improved`, or
`suggested`, and retain source_trace where possible. The clarification answers
below are optional. When answers are provided, apply each answer to the improved
requirements, acceptance criteria, assumptions, risks, and architecture details
where relevant. Do not silently ignore an answer, and do not delete or overwrite
the original source text. When the answers object is empty, use the source text
and clearly labeled project context without presenting context as extracted
source. Include every extracted requirement and produce test coverage for all
extracted and suggested functionality. Return ONLY valid JSON:
{{
  "title": "...",
  "summary": "...",
  "suitable_domain": "...",
  "recommended_tech_stack": {{}},
  "summary": "...",
  "functional_requirements": [{{"id": "FR-001", "title": "...", "description": "...", "acceptance_criteria": [], "origin": "improved", "source_trace": "..."}}],
  "non_functional_requirements": [{{"id": "NFR-001", "category": "...", "description": "...", "acceptance_criteria": [], "origin": "improved", "source_trace": "..."}}],
  "user_stories": [{{"id": "US-001", "story": "...", "acceptance_criteria": []}}],
  "assumptions": [],
  "risks": [],
  "missing_requirements": [],
  "suggested_additions": [],
  "suggestions": [],
  "diagram_sources": {{"class_diagram": "...", "er_diagram": "...", "architecture_diagram": "...", "use_case_diagram": "...", "data_flow_diagram": "...", "sequence_diagram": "..."}},
  "change_summary": {{"added": [], "improved": [], "unchanged": [], "removed": []}}
}}

Source document:
{document}

Additional user-provided project context (context only; preserve the source document separately):
{context}

Optional clarification answers (JSON object; {{}} means no answers were provided):
{answers}
"""
