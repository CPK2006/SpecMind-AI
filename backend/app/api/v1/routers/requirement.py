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
from app.schemas.api_response import APIResponse
from app.schemas.analysis import RequirementAnalysisResponse
from app.schemas.report import ReportResponse
from app.schemas.quality import QualityResponse
from app.schemas.requirement import RequirementResponse
from app.schemas.test_case import TestCaseResponse
from app.services.requirement_service import RequirementService

router = APIRouter(
    prefix="/requirements",
    tags=["Requirements"],
)


@router.post(
    "/upload",
    response_model=APIResponse[RequirementResponse],
    status_code=status.HTTP_201_CREATED,
)
def upload_requirement(
    project_id: uuid.UUID = Form(...),
    title: str = Form(...),
    description: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    result = RequirementService.upload_requirement(
        db=db,
        project_id=project_id,
        title=title,
        description=description,
        file=file,
    )

    return APIResponse(
        success=True,
        message="Requirement uploaded successfully.",
        data=result,
    )


@router.post(
    "/{requirement_id}/analyze",
    response_model=APIResponse[RequirementAnalysisResponse],
)
def analyze_requirement(
    requirement_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    result = RequirementService.analyze_requirement(
        db=db,
        requirement_id=requirement_id,
    )

    return APIResponse(
        success=True,
        message="Requirement analyzed successfully.",
        data=result,
    )


@router.post(
    "/{requirement_id}/test-cases",
    response_model=APIResponse[TestCaseResponse],
)
def generate_test_cases(
    requirement_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    result = RequirementService.generate_test_cases(
        db=db,
        requirement_id=requirement_id,
    )

    return APIResponse(
        success=True,
        message="Test cases generated successfully.",
        data=result,
    )


@router.post(
    "/{requirement_id}/quality-check",
    response_model=APIResponse[QualityResponse],
)
def quality_check(
    requirement_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    result = RequirementService.check_requirement_quality(
        db=db,
        requirement_id=requirement_id,
    )

    return APIResponse(
        success=True,
        message="Requirement quality checked successfully.",
        data=result,
    )


@router.post(
    "/{requirement_id}/generate-report",
    response_model=APIResponse[ReportResponse],
)
def generate_report(
    requirement_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    result = RequirementService.generate_report(
        db=db,
        requirement_id=requirement_id,
    )

    return APIResponse(
        success=True,
        message="Report generated successfully.",
        data=result,
    )