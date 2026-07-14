from __future__ import annotations

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