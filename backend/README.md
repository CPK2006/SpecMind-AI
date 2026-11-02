# SpecMind AI Backend

The backend is a FastAPI service that powers authentication, project workspaces, AI-driven requirement workflows, document processing, quality analysis, diagrams, and exports.

## Responsibilities

- JWT registration and login
- Project ownership and workspace persistence
- Pitch-to-SRS generation
- PDF/DOCX upload and text extraction
- Requirement analysis and quality review
- Test-case generation
- Clarification-question and answer workflows
- Mermaid diagram generation and repair
- DOCX SRS export
- AI provider failover and cooldown handling

## Stack

- Python 3.14+
- FastAPI and Uvicorn
- SQLAlchemy and Alembic
- PostgreSQL
- Pydantic settings and schemas
- JWT and Argon2 password hashing
- Ollama, NVIDIA, OpenRouter, and Gemini integrations

## Setup

Run from `backend`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with a PostgreSQL connection string, a strong `SECRET_KEY`, and one or more AI provider credentials. `backend/.env` is intentionally ignored and must never be committed.

Apply the schema and start the API:

```powershell
alembic upgrade head
python -m uvicorn app.main:app --reload --port 8000
```

Useful URLs:

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Health check: `http://localhost:8000/health`
- API prefix: `http://localhost:8000/api/v1`

## AI provider configuration

Requests can use local Ollama and hosted NVIDIA, OpenRouter, and Gemini providers. Configure the relevant variables in `.env`:

- `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT_SECONDS`
- `NVIDIA_API_KEY`, `NVIDIA_MODEL`
- `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`
- `GEMINI_API_KEYS`, `GEMINI_API_KEY1`, or legacy `GEMINI_API_KEY`

Provider errors are handled by the AI service so configured fallbacks can continue processing. A provider with a billing failure is temporarily cooled down rather than retried on every request.

## API workflow surface

- `auth.py` — register and login
- `project.py` — project CRUD, workspace retrieval, SRS generation, diagram repair, DOCX export
- `requirement.py` — upload, analyze, test generation, quality review, report generation, clarification, and refactoring

Use the generated Swagger contract for exact payloads and response envelopes.

## Tests

```powershell
pip install -r requirements-dev.txt
python -m pytest
```

The test suite includes parser, AI failover, provider, ownership, upload, diagram, and workflow normalization coverage.
