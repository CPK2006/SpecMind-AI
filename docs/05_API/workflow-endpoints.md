# Workflow API

All endpoints use the `/api/v1` prefix and the `{success, message, data}` response envelope.

## Project setup

- `POST /projects` — create a project with `creation_mode` equal to `pitch` or `upload`.
- `GET /projects` — list previous projects.
- `GET /projects/{project_id}/workspace` — load saved SRS or improvement workspace data for dashboard projects.
- `GET /projects/{project_id}/export/docx` — export the complete SRS as DOCX.
- `POST /projects/{project_id}/generate-srs` — generate an SRS from a pitch project.

## Existing SRS improvement

- `POST /requirements/upload` — upload a PDF/DOCX into a project.
- `POST /requirements/{requirement_id}/analyze` — analyze extracted requirements.
- `POST /requirements/{requirement_id}/test-cases` — generate test cases.
- `POST /requirements/{requirement_id}/quality-check` — review requirement quality.
- `POST /requirements/{requirement_id}/generate-report` — run the three operations and return the combined report.
- `POST /requirements/{requirement_id}/clarification-answers` — apply answers, regenerate the refactored SRS and linked tests, and return the newly saved combined report.

Workspace results and clarification refinements are persisted so users can return from the dashboard after leaving or reloading the page. The DOCX export includes the generated requirements, user stories, risks, assumptions, test cases, diagram source, and (for uploads) original extracted text. The frontend also exports complete Markdown and JSON, renders Mermaid diagrams with source available, and uses browser print-to-PDF.

AI generation uses a shared failover path: NVIDIA, OpenRouter, then Gemini. Configure optional `NVIDIA_API_KEY`, `OPENROUTER_API_KEY`, and comma-separated `GEMINI_API_KEYS` in the ignored `backend/.env`; the legacy `GEMINI_API_KEY` is still supported. NVIDIA defaults to `z-ai/glm-5.3`. OpenRouter defaults to `openrouter/auto` with its low cost-tier preference (this is not a spend cap). Gemini keys rotate their starting position between requests and remaining keys are tried in the same request. Provider failures are sanitized and source-based drafts remain available if all providers fail. A provider with a billing/payment issue is skipped temporarily, then failover continues. Tests should mock provider calls rather than contact live services.
