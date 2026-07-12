
from app.database.init_db import check_database
from fastapi import FastAPI
from app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    description="AI-Powered Requirements Intelligence Platform",
    version=settings.app_version,
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