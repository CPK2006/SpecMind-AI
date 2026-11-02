# Deployment

Deployment documentation covers how to run SpecMind AI outside local development.

## Runtime components

1. React/Vite frontend
2. FastAPI/Uvicorn backend
3. PostgreSQL database
4. Optional Ollama or hosted AI providers
5. Durable storage for uploaded documents and generated exports

Deployment plans must define environment variables, secret injection, database migrations, CORS origins, upload storage, health checks, logging, provider availability, and rollback behavior. The `docker/` directory is reserved for container and deployment assets; no production container definition is currently committed.
