from __future__ import annotations

import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.services.requirement_service import RequirementService
from app.schemas.analysis import RequirementAnalysisResponse
router = APIRouter(
    prefix="/requirements",
    tags=["Requirements"],
)
from app.schemas.test_case import TestCaseResponse



@router.post(
    "/upload",
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


@router.post(
    "/{requirement_id}/analyze",
    response_model=RequirementAnalysisResponse,
)
def analyze_requirement(
    requirement_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    try:
        return RequirementService.analyze_requirement(
            db=db,
            requirement_id=requirement_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
@router.post(
    "/{requirement_id}/test-cases",
    response_model=TestCaseResponse,
)

def generate_test_cases(
    requirement_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    try:
        return RequirementService.generate_test_cases(
            db,
            requirement_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )