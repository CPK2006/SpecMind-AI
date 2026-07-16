from __future__ import annotations
import uuid

from sqlalchemy.orm import Session

from app.models.requirement import Requirement



class RequirementRepository:

    @staticmethod
    def create_requirement(
        db: Session,
        requirement: Requirement,
    ) -> Requirement:

        db.add(requirement)
        db.commit()
        db.refresh(requirement)

        return requirement
    @staticmethod
    def get_requirement_by_id(
        db: Session,
        requirement_id: uuid.UUID,
    ) -> Requirement | None:

     return (
        db.query(Requirement)
        .filter(Requirement.id == requirement_id)
        .first()
    )