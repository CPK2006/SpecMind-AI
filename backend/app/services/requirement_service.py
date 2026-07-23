from __future__ import annotations

import json
import uuid

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.ai.gemini_service import GeminiService
from app.core.exceptions import (
    RequirementNotFoundError,
    ExtractedTextNotFoundError,
)
from app.core.logger import logger
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

        logger.info(
            "Uploading requirement: %s",
            document_name,
        )

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

        saved_requirement = RequirementRepository.create_requirement(
            db,
            requirement,
        )

        logger.info(
            "Requirement uploaded successfully: %s",
            saved_requirement.title,
        )

        return saved_requirement

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
            raise RequirementNotFoundError()

        if not requirement.extracted_text:
            raise ExtractedTextNotFoundError()

        # Return cached analysis
        if requirement.analysis_result:
            logger.info(
                "Analysis cache hit for requirement %s",
                requirement.id,
            )
            return json.loads(requirement.analysis_result)

        logger.info(
            "Analysis cache miss. Calling Gemini..."
        )

        gemini = GeminiService()

        result = gemini.analyze_requirements(
            requirement.extracted_text,
        )

        RequirementRepository.save_analysis_result(
            db,
            requirement,
            json.dumps(result),
        )

        logger.info(
            "Analysis completed successfully."
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
            raise RequirementNotFoundError()

        if not requirement.extracted_text:
            raise ExtractedTextNotFoundError()

        # Return cached test cases
        if requirement.test_cases_result:
            logger.info(
                "Test case cache hit for requirement %s",
                requirement.id,
            )
            return json.loads(requirement.test_cases_result)

        logger.info(
            "Test case cache miss. Calling Gemini..."
        )

        gemini = GeminiService()

        result = gemini.generate_test_cases(
            requirement.extracted_text,
        )

        RequirementRepository.save_test_cases_result(
            db,
            requirement,
            json.dumps(result),
        )

        logger.info(
            "Test cases generated successfully."
        )

        return result

    @staticmethod
    def check_requirement_quality(
        db: Session,
        requirement_id: uuid.UUID,
    ) -> dict:

        requirement = RequirementRepository.get_requirement_by_id(
            db,
            requirement_id,
        )

        if requirement is None:
            raise RequirementNotFoundError()

        if not requirement.extracted_text:
            raise ExtractedTextNotFoundError()

        # Return cached quality report
        if requirement.quality_result:
            logger.info(
                "Quality cache hit for requirement %s",
                requirement.id,
            )
            return json.loads(requirement.quality_result)

        logger.info(
            "Quality cache miss. Calling Gemini..."
        )

        gemini = GeminiService()

        result = gemini.check_requirement_quality(
            requirement.extracted_text,
        )

        RequirementRepository.save_quality_result(
            db,
            requirement,
            json.dumps(result),
        )

        logger.info(
            "Quality report generated successfully."
        )

        return result

    @staticmethod
    def generate_report(
        db: Session,
        requirement_id: uuid.UUID,
    ) -> dict:

        logger.info(
            "Generating complete report for requirement %s",
            requirement_id,
        )

        report = {
            "analysis": RequirementService.analyze_requirement(
                db,
                requirement_id,
            ),
            "test_cases": RequirementService.generate_test_cases(
                db,
                requirement_id,
            ),
            "quality": RequirementService.check_requirement_quality(
                db,
                requirement_id,
            ),
        }

        logger.info(
            "Report generated successfully."
        )

        return report