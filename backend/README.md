
# SpecMind AI Backend

FastAPI backend for the two SpecMind workflows:

- **Pitch**: create a project from an idea and generate a structured SRS through `POST /api/v1/projects/{project_id}/generate-srs`.
- **Upload**: upload a PDF/DOCX SRS, then analyze it, generate test cases, run quality review, and combine results through `POST /api/v1/requirements/{requirement_id}/generate-report`.

## Local setup

Run commands from this directory. Copy `.env.example` to `.env`, set PostgreSQL plus one or more AI provider keys, then apply migrations. Requests fail over through NVIDIA, OpenRouter, and Gemini in that order. `GEMINI_API_KEYS` accepts a comma-separated key list; legacy `GEMINI_API_KEY` remains supported. NVIDIA defaults to the currently listed `z-ai/glm-5.3`; OpenRouter defaults to `openrouter/auto`. Provider models can be changed with `NVIDIA_MODEL` and `OPENROUTER_MODEL`. OpenRouter's low cost tier is a routing preference, not a fixed spend cap. A provider with a billing error is skipped for five minutes while the request continues to the next configured provider. Never commit `.env`; rotate credentials that have been shared or exposed:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --reload --port 8000
```

Swagger documentation is available at `http://localhost:8000/docs`.

Install `requirements-dev.txt` to run the backend regression suite with `python -m pytest`.
Project workspaces are available at `GET /api/v1/projects/{project_id}/workspace`; use `GET /api/v1/projects/{project_id}/export/docx` for a complete DOCX SRS export.

The current frontend authentication is browser-local and is not a security boundary. Production authentication and project ownership must be added before deployment.
