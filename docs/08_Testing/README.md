# Testing

Testing documentation defines how SpecMind AI is validated across the frontend, backend, integrations, and user workflows.

## Current validation surfaces

- Backend regression tests under `backend/tests/`
- Frontend tests under `frontend/tests/`
- Frontend production build with `npm run build`
- API health and Swagger startup checks
- Database migration validation with `alembic upgrade head`

Backend tests should mock external AI providers and cover failover, parsing, ownership, uploads, diagrams, and workflow normalization. Add behavioral scenarios for new user-visible workflows, including success, validation, provider failure, and persistence paths.
