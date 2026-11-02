
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectRepository:

    @staticmethod
    def create_project(
        db: Session,
        project: ProjectCreate,
        owner_id: uuid.UUID,
    ) -> Project:
        db_project = Project(
            name=project.name,
            description=project.description,
            project_type=project.project_type,
            creation_mode=project.creation_mode,
            idea_pitch=project.idea_pitch,
            user_id=owner_id,
        )

        db.add(db_project)
        db.commit()
        db.refresh(db_project)

        return db_project

    @staticmethod
    def list_projects(
        db: Session,
        owner_id: uuid.UUID,
    ) -> list[Project]:
        return (
            db.query(Project)
            .filter(Project.user_id == owner_id)
            .all()
        )

    @staticmethod
    def get_project_by_id(
        db: Session,
        project_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> Project | None:
        return (
            db.query(Project)
            .filter(
                Project.id == project_id,
                Project.user_id == owner_id,
            )
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

    @staticmethod
    def save_generated_srs(
        db: Session,
        project: Project,
        result: str,
    ) -> Project:
        project.generated_srs_result = result
        project.status = "Complete"
        db.commit()
        db.refresh(project)
        return project
