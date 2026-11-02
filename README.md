# SpecMind AI

<p align="center">
  <strong>Turn ideas and existing specifications into implementation-ready software requirements.</strong>
</p>

<p align="center">
  <a href="https://github.com/CPK2006/SpecMind-AI">Repository</a> ·
  <a href="http://localhost:5173">Web app</a> ·
  <a href="http://localhost:8000/docs">API docs</a>
</p>

SpecMind AI is an AI-powered requirements intelligence platform for teams that want to move from ambiguous ideas to clear, testable, traceable engineering work. It combines a React workspace with a FastAPI API, PostgreSQL persistence, document parsing, multi-provider AI orchestration, quality review, test generation, diagram generation, and exportable SRS reports.

> **Project status:** Working local MVP. The core pitch and SRS-improvement workflows are implemented. Production hardening, deployment automation, and operational authentication policy are still in progress.

## What SpecMind does

### 1. Pitch an idea

Start with a product idea and context. SpecMind creates a project and generates a structured software requirements specification containing:

- Functional and non-functional requirements
- User stories and acceptance criteria
- Generated test cases
- Requirement quality and confidence signals
- Mermaid-compatible architecture and UML diagram source
- An assembled SRS ready for review or export

### 2. Improve an existing SRS

Upload a PDF or DOCX specification. SpecMind extracts the document text, analyzes requirement quality, identifies gaps, generates tests, proposes clarifying questions, and creates a refined improvement workspace without changing the original upload.

The workspace supports:

- Extracted and refined requirements
- Quality issues and recommendations
- Clarification questions and answer-driven regeneration
- Selectable use cases
- Rendered diagrams and editable diagram source
- Linked test cases
- Refactored SRS content
- Change and quality reports
- Project reopening from the dashboard

## Product highlights

| Capability | Outcome |
| --- | --- |
| Requirements intelligence | Convert product intent into structured engineering artifacts |
| Quality review | Surface ambiguity, missing constraints, risks, and improvement opportunities |
| Test generation | Produce testable scenarios alongside requirements |
| Traceability workspace | Keep requirements, tests, diagrams, and reports together |
| AI provider resilience | Route across Ollama, NVIDIA, OpenRouter, and Gemini with failover |
| Document workflows | Parse PDF/DOCX inputs and export generated SRS documents |
| Diagram intelligence | Generate and repair Mermaid architecture/UML diagrams |
| Project persistence | Save workspaces, reports, and project history in PostgreSQL |

## Technology stack

### Frontend

- **React 18** for the application UI
- **Vite 5** for development and production builds
- **Axios** for API communication
- **Mermaid** and diagram utilities for visualizing generated architecture/UML content
- CSS-based responsive workspace styling

### Backend

- **Python 3.14+** runtime
- **FastAPI** REST API with OpenAPI/Swagger documentation
- **SQLAlchemy** data access and **Alembic** migrations
- **PostgreSQL** database
- **Pydantic settings and schemas**
- **JWT authentication** with password hashing
- PDF/DOCX parsing and DOCX export

### AI and integrations

- **Ollama** for local model execution
- **NVIDIA** as the primary hosted provider when configured
- **OpenRouter** as a hosted fallback
- **Google Gemini** with configurable key rotation
- Provider health cooldowns and request failover

## Repository map

```text
.
├── backend/       FastAPI app, AI services, migrations, tests, uploads
├── frontend/      React/Vite web application
├── docs/          Product, architecture, API, AI, testing, and deployment docs
├── database/      Database documentation and workspace placeholder
├── docker/        Container/deployment documentation and workspace placeholder
├── assets/        Static project assets
├── prompts/       Prompt resources and guidance
├── knowledge/     Domain knowledge and requirement resources
├── examples/      Example artifacts
├── scripts/       Operational and developer scripts
└── legacy/        Retained legacy materials
```

## Run locally

### Prerequisites

- Python 3.14 or a compatible supported Python version
- Node.js and npm
- PostgreSQL
- Optional AI provider credentials, or a local Ollama installation

### Configure the backend

```powershell
Copy-Item backend\.env.example backend\.env
# Edit backend\.env with DATABASE_URL, SECRET_KEY, and provider credentials
```

Never commit `backend/.env`. It is ignored by Git; use `backend/.env.example` as the safe configuration template.

### Start the backend

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --reload --port 8000
```

Backend endpoints:

- API base: `http://localhost:8000/api/v1`
- Swagger UI: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### Start the frontend

In a second terminal:

```powershell
Set-Location frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Set `VITE_API_URL` if the API is hosted somewhere other than the default `http://localhost:8000/api/v1`.

## Development and validation

```powershell
# Frontend
Set-Location frontend
npm run build
npm test

# Backend
Set-Location backend
pip install -r requirements-dev.txt
python -m pytest
```

The backend tests cover AI failover, provider behavior, parsing, ownership, diagram repair, upload flows, and workflow normalization. The frontend test suite covers diagram behavior.

## API areas

- `/api/v1/auth` — registration and login
- `/api/v1/projects` — create, list, update, delete, reopen, generate SRS, repair diagrams, and export DOCX
- `/api/v1/requirements` — upload, analyze, generate tests, quality review, reports, clarification questions, refactoring, and answer submission

The generated OpenAPI contract at `/docs` is the authoritative reference for request and response schemas.

## Security and production notes

- Keep all API keys and database credentials in the ignored `backend/.env`.
- Use a long random `SECRET_KEY` outside local development.
- Review CORS origins, database permissions, upload limits, and logging before deployment.
- AI provider credentials should be rotated if exposed.
- Run migrations before starting a new environment.

## License

MIT
