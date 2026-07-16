from __future__ import annotations

import json
import uuid

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.ai.gemini_service import GeminiService
from app.models.requirement import Requirement
from app.repositories.requirement_repository import RequirementRepository
from app.utils.document_parser import extract_text
from app.utils.file_storage import save_uploaded_file


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

        try:
            extracted_text = extract_text(document_path)
        except Exception:
            extracted_text = None

        requirement = Requirement(
            project_id=project_id,
            title=title,
            description=description,
            document_name=document_name,
            document_path=document_path,
            extracted_text=extracted_text,
            status="Uploaded",
        )

        return RequirementRepository.create_requirement(
            db,
            requirement,
        )

    @staticmethod
    def analyze_requirement(
        db: Session,
        requirement_id: uuid.UUID,
    ) -> dict:

        requirement = RequirementRepository.get_requirement_by_id(
            db,
            requirement_id,
        )

        if requirement is None:
            raise ValueError("Requirement not found.")

        if not requirement.extracted_text:
            raise ValueError("No extracted text found.")

        # Return cached analysis if available
        if requirement.analysis_result:
            return json.loads(requirement.analysis_result)

        gemini = GeminiService()

        result = gemini.analyze_requirements(
            requirement.extracted_text,
        )

        RequirementRepository.save_analysis_result(
            db,
            requirement,
            json.dumps(result),
        )

        return result
    
    @staticmethod
    def generate_test_cases(
        db: Session,
        requirement_id: uuid.UUID,
    ) -> dict:
    
        requirement = RequirementRepository.get_requirement_by_id(
            db,
            requirement_id,
        )
    
        if requirement is None:
            raise ValueError("Requirement not found.")
    
        if not requirement.extracted_text:
            raise ValueError("No extracted text found.")
    
        gemini = GeminiService()
    
        return gemini.generate_test_cases(
            requirement.extracted_text,
        )