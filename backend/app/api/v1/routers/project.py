from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.schemas.api_response import APIResponse
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
)
from app.services.project_service import ProjectService

router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
)


@router.post(
    "",
    response_model=APIResponse[ProjectResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
):
    try:
        result = ProjectService.create_project(db, project)

        return APIResponse[ProjectResponse](
            success=True,
            message="Project created successfully.",
            data=ProjectResponse.model_validate(result),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "",
    response_model=APIResponse[list[ProjectResponse]],
)
def list_projects(
    db: Session = Depends(get_db),
):
    result = ProjectService.list_projects(db)

    return APIResponse[list[ProjectResponse]](
    success=True,
    message="Projects retrieved successfully.",
    data=[
        ProjectResponse.model_validate(project)
        for project in result
    ],
)


@router.get(
    "/{project_id}",
    response_model=APIResponse[ProjectResponse],
)
def get_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    project = ProjectService.get_project_by_id(
        db,
        project_id,
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    return APIResponse(
        success=True,
        message="Project retrieved successfully.",
        data=project,
    )


@router.put(
    "/{project_id}",
    response_model=APIResponse[ProjectResponse],
)
def update_project(
    project_id: uuid.UUID,
    project: ProjectUpdate,
    db: Session = Depends(get_db),
):
    db_project = ProjectService.get_project_by_id(
        db,
        project_id,
    )

    if db_project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    result = ProjectService.update_project(
        db,
        db_project,
        project,
    )

    return APIResponse[ProjectResponse](
    success=True,
    message="Project updated successfully.",
    data=ProjectResponse.model_validate(result),
)


@router.delete(
    "/{project_id}",
    response_model=APIResponse[None],
)
def delete_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    db_project = ProjectService.get_project_by_id(
        db,
        project_id,
    )

    if db_project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    ProjectService.delete_project(
        db,
        db_project,
    )

    return APIResponse(
        success=True,
        message="Project deleted successfully.",
        data=None,
    )