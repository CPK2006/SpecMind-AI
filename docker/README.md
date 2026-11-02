# Docker and deployment

This directory is reserved for container and deployment assets for SpecMind AI.

The current local development path runs PostgreSQL separately, starts the FastAPI backend with Uvicorn, and runs the React frontend with Vite. Container definitions can be added here when deployment targets and environment-management rules are finalized.

Any future image must receive secrets at runtime rather than copying `.env` files into an image.
