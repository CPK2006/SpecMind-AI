# Architecture

Architecture documentation explains how the SpecMind AI system is structured and how its components communicate.

## Current architecture

- **Frontend:** React/Vite workspace in `frontend/`
- **Backend:** FastAPI service in `backend/`
- **Persistence:** PostgreSQL accessed through SQLAlchemy
- **Schema evolution:** Alembic migrations
- **AI orchestration:** local Ollama plus NVIDIA, OpenRouter, and Gemini providers
- **Document flow:** PDF/DOCX upload, extraction, analysis, persistence, and export

Architecture records should identify boundaries, dependencies, data ownership, failure behavior, and security considerations. Update this section when a new service, integration, or persistence boundary is introduced.
