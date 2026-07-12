from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.project_service import ProjectService

router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
)


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
):
    try:
        return ProjectService.create_project(db, project)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "",
    response_model=list[ProjectResponse],
)
def list_projects(
    db: Session = Depends(get_db),
):
    return ProjectService.list_projects(db)


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
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

    return project


@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
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

    return ProjectService.update_project(
        db,
        db_project,
        project,
    )


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
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