# Database

SpecMind AI uses PostgreSQL as its application database.

## Schema ownership

The live schema is defined by SQLAlchemy models under `backend/app/models/` and versioned with Alembic migrations under `backend/alembic/versions/`.

Run migrations from `backend`:

```powershell
alembic upgrade head
```

Create a new migration after a model change:

```powershell
alembic revision --autogenerate -m "describe schema change"
```

Configure the connection with `DATABASE_URL` in the ignored `backend/.env`. Do not commit credentials, dumps, or local database files.
