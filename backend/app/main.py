from fastapi import FastAPI
from app.api.v1.routers.requirement import router as requirement_router
from app.api.v1.routers.project import router as project_router
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.database.init_db import check_database

app = FastAPI(
    title=settings.app_name,
    description="AI-Powered Requirements Intelligence Platform",
    version=settings.app_version,
)

# Register global exception handlers
register_exception_handlers(app)

# Register API routers
app.include_router(project_router, prefix="/api/v1")
app.include_router(
    requirement_router,
    prefix="/api/v1",
)


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