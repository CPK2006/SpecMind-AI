from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.project import Project
from app.repositories import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:

    @staticmethod
    def create_project(
        db: Session,
        project: ProjectCreate,
    ) -> Project:

        existing_projects = ProjectRepository.list_projects(db)

        for existing in existing_projects:
            if existing.name.lower() == project.name.lower():
                raise ValueError(
                    "A project with this name already exists."
                )

        return ProjectRepository.create_project(
            db,
            project,
        )

    @staticmethod
    def list_projects(
        db: Session,
    ) -> list[Project]:

        return ProjectRepository.list_projects(db)

    @staticmethod
    def get_project_by_id(
        db: Session,
        project_id: uuid.UUID,
    ) -> Project | None:

        return ProjectRepository.get_project_by_id(
            db,
            project_id,
        )

    @staticmethod
    def update_project(
        db: Session,
        db_project: Project,
        project: ProjectUpdate,
    ) -> Project:

        return ProjectRepository.update_project(
            db,
            db_project,
            project,
        )

    @staticmethod
    def delete_project(
        db: Session,
        db_project: Project,
    ) -> None:

        ProjectRepository.delete_project(
            db,
            db_project,
        )