from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.requirement import Requirement
from app.repositories.requirement_repository import RequirementRepository
from app.utils.file_storage import save_uploaded_file
from fastapi import UploadFile


class RequirementService:

    @staticmethod
    def upload_requirement(
        db: Session,
        project_id: uuid.UUID,
        title: str,
        description: str | None,
        file: UploadFile,
    ) -> Requirement:

        document_name, document_path = save_uploaded_file(file)

        requirement = Requirement(
            project_id=project_id,
            title=title,
            description=description,
            document_name=document_name,
            document_path=document_path,
            status="Uploaded",
        )

        return RequirementRepository.create_requirement(
            db,
            requirement,
        )