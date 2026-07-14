from __future__ import annotations

import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.schemas.requirement import RequirementResponse
from app.services.requirement_service import RequirementService

router = APIRouter(
    prefix="/requirements",
    tags=["Requirements"],
)


@router.post(
    "/upload",
    response_model=RequirementResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_requirement(
    project_id: uuid.UUID = Form(...),
    title: str = Form(...),
    description: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    return RequirementService.upload_requirement(
        db=db,
        project_id=project_id,
        title=title,
        description=description,
        file=file,
    )