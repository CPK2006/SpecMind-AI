# Database

Database documentation describes PostgreSQL persistence for users, projects, uploaded requirements, generated analysis, tests, quality results, reports, and saved workspaces.

The implementation source is split between SQLAlchemy models in `backend/app/models/` and Alembic migrations in `backend/alembic/versions/`. Apply the current schema from `backend` with:

```powershell
alembic upgrade head
```

Database documents should cover entities, relationships, ownership constraints, migration strategy, indexes, retention, and backup considerations. Never include credentials or production data.
