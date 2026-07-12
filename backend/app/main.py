from fastapi import FastAPI

from app.api.v1.routers.project import router as project_router
from app.core.config import settings
from app.database.init_db import check_database

app = FastAPI(
    title=settings.app_name,
    description="AI-Powered Requirements Intelligence Platform",
    version=settings.app_version,
)

# Register API routers
app.include_router(project_router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "message": f"Welcome to {settings.app_name} 🚀"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.on_event("startup")
def startup():
    check_database()