from __future__ import annotations

import json
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
from app.ai.gemini_service import GeminiService
from app.repositories.requirement_repository import RequirementRepository
from app.schemas.api_response import APIResponse
from app.schemas.analysis import RequirementAnalysisResponse
from app.schemas.quality import QualityResponse
from app.schemas.requirement import RequirementResponse
from app.schemas.test_case import TestCaseResponse
from app.services.requirement_service import RequirementService
from pydantic import BaseModel, Field


class ClarificationAnswersRequest(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)

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
    try:
        result = RequirementService.upload_requirement(
            db=db,
            project_id=project_id,
            title=title,
            description=description,
            file=file,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return APIResponse(
        success=True,
        message="Requirement uploaded successfully.",
        data=result,
    )


@router.post(
    "/{requirement_id}/analyze",
    response_model=APIResponse[dict],
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
    response_model=APIResponse[dict],
)
def generate_report(
    requirement_id: uuid.UUID,
    refresh: bool = False,
    db: Session = Depends(get_db),
):
    result = RequirementService.generate_report(
        db=db,
        requirement_id=requirement_id,
        refresh=refresh,
    )

    return APIResponse(
        success=True,
        message="Report generated successfully.",
        data=result,
    )


@router.post(
    "/{requirement_id}/clarification-questions",
    response_model=APIResponse[dict],
)
def clarification_questions(
    requirement_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    requirement = RequirementRepository.get_requirement_by_id(db, requirement_id)
    if requirement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found.")
    if not requirement.extracted_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No extracted text found.")
    result = GeminiService().generate_clarification_questions(requirement.extracted_text, requirement.project.description)
    requirement.clarification_questions_result = json.dumps(result)
    db.commit()
    return APIResponse(success=True, message="Clarification questions generated successfully.", data=result)


@router.post(
    "/{requirement_id}/refactor",
    response_model=APIResponse[dict],
)
def refactor_requirement(
    requirement_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    requirement = RequirementRepository.get_requirement_by_id(db, requirement_id)
    if requirement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found.")
    if not requirement.extracted_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No extracted text found.")
    result = GeminiService().refactor_srs(requirement.extracted_text, context=requirement.project.description)
    requirement.refactored_srs_result = json.dumps(result)
    db.commit()
    return APIResponse(success=True, message="SRS refactored successfully.", data=result)


@router.post(
    "/{requirement_id}/clarification-answers",
    response_model=APIResponse[dict],
)
def submit_clarification_answers(
    requirement_id: uuid.UUID,
    payload: ClarificationAnswersRequest,
    db: Session = Depends(get_db),
):
    result = RequirementService.apply_clarification_answers(db, requirement_id, payload.answers)
    return APIResponse(success=True, message="Clarification answers applied successfully.", data=result)
