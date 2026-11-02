# API

This section documents the HTTP contract exposed by the FastAPI backend.

## Current artifacts

- [workflow-endpoints.md](./workflow-endpoints.md) — project and requirement workflow endpoints

The API uses the `/api/v1` prefix and a `{success, message, data}` response envelope. Swagger and the generated OpenAPI contract are available at `http://localhost:8000/docs` when the backend is running.

When documenting an endpoint, include authentication requirements, request and response examples, validation rules, ownership behavior, errors, and side effects such as persisted workspace updates or generated files.
