from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectRepository:

    @staticmethod
    def create_project(db: Session, project: ProjectCreate) -> Project:
        db_project = Project(
            name=project.name,
            description=project.description,
            project_type=project.project_type,
        )

        db.add(db_project)
        db.commit()
        db.refresh(db_project)

        return db_project

    @staticmethod
    def list_projects(db: Session) -> list[Project]:
        return db.query(Project).all()

    @staticmethod
    def get_project_by_id(
        db: Session,
        project_id: uuid.UUID,
    ) -> Project | None:
        return (
            db.query(Project)
            .filter(Project.id == project_id)
            .first()
        )

    @staticmethod
    def update_project(
        db: Session,
        db_project: Project,
        project: ProjectUpdate,
    ) -> Project:

        update_data = project.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(db_project, key, value)

        db.commit()
        db.refresh(db_project)

        return db_project

    @staticmethod
    def delete_project(
        db: Session,
        db_project: Project,
    ) -> None:
        db.delete(db_project)
        db.commit()