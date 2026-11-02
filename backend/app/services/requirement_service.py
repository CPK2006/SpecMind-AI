from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.ai.gemini_service import AIProviderUnavailableError, GeminiService
from app.core.exceptions import (
    RequirementNotFoundError,
    ExtractedTextNotFoundError,
)
from app.core.logger import logger
from app.models.requirement import Requirement
from app.repositories.requirement_repository import RequirementRepository
from app.repositories.project_repository import ProjectRepository
from app.utils.document_parser import extract_text
from app.utils.file_storage import save_uploaded_file


class RequirementService:

    @staticmethod
    def upload_requirement(
        db: Session,
        project_id: uuid.UUID,
        owner_id: uuid.UUID,
        title: str,
        description: str | None,
        file: UploadFile,
    ) -> Requirement:

        if ProjectRepository.get_project_by_id(db, project_id, owner_id) is None:
            raise ValueError("Project not found.")

        document_name, document_path = save_uploaded_file(file)

        logger.info(
            "Uploading requirement: %s",
            document_name,
        )

        try:
            extracted_text = extract_text(document_path)
        except Exception as exc:
            Path(document_path).unlink(missing_ok=True)
            logger.exception("Document extraction failed for %s", document_name)
            raise ValueError("Unable to extract text from the uploaded document.") from exc

        if not extracted_text or not extracted_text.strip():
            Path(document_path).unlink(missing_ok=True)
            raise ValueError("The uploaded document does not contain readable text.")

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
            "Analysis cache miss. Calling AI provider failover..."
        )

        gemini = GeminiService()

        result = gemini.analyze_requirements(
            requirement.extracted_text,
            requirement.project.description,
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
            "Test case cache miss. Calling AI provider failover..."
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
            "Quality cache miss. Calling AI provider failover..."
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
        *,
        refresh: bool = False,
    ) -> dict:

        logger.info(
            "Generating complete report for requirement %s",
            requirement_id,
        )

        requirement = RequirementRepository.get_requirement_by_id(db, requirement_id)
        if requirement is None:
            raise RequirementNotFoundError()
        if requirement.improvement_report_result and not refresh:
            return json.loads(requirement.improvement_report_result)
        had_cached_analysis = bool(requirement.analysis_result)
        try:
            analysis = RequirementService.analyze_requirement(db, requirement_id)
        except AIProviderUnavailableError as exc:
            logger.warning("Requirement analysis unavailable for %s; saving source-based draft: %s", requirement_id, exc.public_summary)
            return RequirementService._save_ai_unavailable_draft(db, requirement, reason=f"{exc.public_summary} The complete extracted source is preserved; review this source-based draft and retry when AI is available.")
        if analysis.get("is_software_document") is False:
            report = {
                "is_software_document": False,
                "source_text": requirement.extracted_text or "",
                "source_text_length": len(requirement.extracted_text or ""),
                "document_name": requirement.document_name,
                "message": analysis.get("message") or "This document does not appear to be a software requirements specification.",
                "functional_requirements": [],
                "non_functional_requirements": [],
                "test_cases": [],
                "clarification_questions": [],
            }
            requirement.improvement_report_result = json.dumps(report)
            db.commit()
            return report

        # Older projects may have a saved extraction analysis but no combined
        # report yet. Assemble a labelled draft from saved data so reopening a
        # project does not depend on another AI call being available.
        if had_cached_analysis and not refresh:
            cached_tests = json.loads(requirement.test_cases_result) if requirement.test_cases_result else {}
            cached_quality = json.loads(requirement.quality_result) if requirement.quality_result else {}
            refactored = json.loads(requirement.refactored_srs_result) if requirement.refactored_srs_result else {}
            if isinstance(refactored, dict) and isinstance(refactored.get("result"), dict):
                refactored = refactored["result"]
            questions = json.loads(requirement.clarification_questions_result) if requirement.clarification_questions_result else {
                "questions": [
                    {"id": "Q-001", "question": "Which user roles need distinct permissions?", "reason": "The source should identify who may perform each major action."},
                    {"id": "Q-002", "question": "What should the system do when an operation fails or required data is invalid?", "reason": "Failure and validation behavior make requirements and tests more precise."},
                    {"id": "Q-003", "question": "Are there expected usage volumes or response-time targets?", "reason": "Concrete targets make performance requirements verifiable."},
                ]
            }
            if not cached_tests:
                draft_cases = []
                for index, raw_item in enumerate(analysis.get("functional_requirements") or [], 1):
                    item = raw_item if isinstance(raw_item, dict) else {"description": str(raw_item)}
                    draft_cases.append({
                        "id": f"TC-DRAFT-{index:03d}",
                        "requirement_id": item.get("id") or f"FR-{index:03d}",
                        "requirement": item.get("title") or item.get("description") or f"Functional requirement {index}",
                        "precondition": "The application is available and required test data is prepared.",
                        "steps": [str(criterion) for criterion in (item.get("acceptance_criteria") or [])]
                        or [f"Exercise the behavior described by functional requirement {index} using valid and invalid inputs."],
                        "expected_result": item.get("description") or "The system follows the documented requirement and handles invalid input safely.",
                    })
                cached_tests = {"test_cases": draft_cases}
            quality = {
                **cached_quality,
                "quality_score": cached_quality.get("quality_score"),
                "confidence_score": cached_quality.get("confidence_score"),
                "issues": cached_quality.get("issues") or [
                    {"severity": "review", "reason": "Scores and recommendations have not yet been recalculated for this draft."}
                ],
            }
            report = GeminiService.normalize_upload_result(
                source_text=requirement.extracted_text or "",
                analysis=analysis,
                test_cases=cached_tests,
                quality=quality,
                refactored=refactored,
                questions=questions,
            )
            report["document_name"] = requirement.document_name
            report["generation_status"] = "draft"
            report["generation_note"] = "This workspace draft uses the saved source analysis. AI refinement, quality scoring, and generated follow-up questions can be completed when the AI service is available."
            requirement.improvement_report_result = json.dumps(report, ensure_ascii=False)
            db.commit()
            return report
        context = requirement.project.description
        try:
            questions = json.loads(requirement.clarification_questions_result) if requirement.clarification_questions_result else GeminiService().generate_clarification_questions(requirement.extracted_text or "", context)
            refactored = json.loads(requirement.refactored_srs_result) if requirement.refactored_srs_result else GeminiService().refactor_srs(requirement.extracted_text or "", context=context)
            if isinstance(refactored, dict) and isinstance(refactored.get("result"), dict):
                refactored = refactored["result"]
            quality = GeminiService().check_requirement_quality(json.dumps(refactored, ensure_ascii=False))
            cases_input = "\n\nRefactored and suggested functionality:\n" + json.dumps({
                "functional_requirements": refactored.get("functional_requirements", []),
                "suggested_additions": refactored.get("suggested_additions", []),
            }, ensure_ascii=False)
            test_cases = GeminiService().generate_test_cases((requirement.extracted_text or "") + cases_input)
        except AIProviderUnavailableError as exc:
            logger.warning("Requirement refinement unavailable for %s; saving source-based draft: %s", requirement_id, exc.public_summary)
            return RequirementService._save_ai_unavailable_draft(db, requirement, reason=f"{exc.public_summary} The complete extracted source is preserved; review this source-based draft and retry when AI is available.")
        db.commit()
        report = GeminiService.normalize_upload_result(source_text=requirement.extracted_text or "", analysis=analysis, test_cases=test_cases, quality=quality, refactored=refactored, questions=questions)
        report["document_name"] = requirement.document_name
        requirement.clarification_questions_result = json.dumps(questions)
        requirement.refactored_srs_result = json.dumps(refactored)
        requirement.test_cases_result = json.dumps(test_cases)
        requirement.quality_result = json.dumps(quality)
        requirement.improvement_report_result = json.dumps(report)
        requirement.status = "Analyzed"
        requirement.project.status = "Complete"
        db.commit()

        logger.info(
            "Report generated successfully."
        )

        return report

    @staticmethod
    def _save_ai_unavailable_draft(db: Session, requirement: Requirement, *, reason: str) -> dict:
        report = GeminiService.draft_upload_result(
            source_text=requirement.extracted_text or "",
            document_name=requirement.document_name,
            reason=reason,
        )
        requirement.analysis_result = json.dumps(report.get("analysis") or {}, ensure_ascii=False)
        requirement.test_cases_result = json.dumps(report.get("test_cases") or [], ensure_ascii=False)
        requirement.quality_result = json.dumps(report.get("quality") or {}, ensure_ascii=False)
        requirement.refactored_srs_result = json.dumps(report.get("refactored_srs") or {}, ensure_ascii=False)
        requirement.clarification_questions_result = json.dumps({"questions": report.get("clarification_questions") or []}, ensure_ascii=False)
        requirement.improvement_report_result = json.dumps(report, ensure_ascii=False)
        requirement.status = "Analyzed"
        requirement.project.status = "Complete"
        db.commit()
        return report

    @staticmethod
    def apply_clarification_answers(db: Session, requirement_id: uuid.UUID, answers: dict[str, str]) -> dict:
        requirement = RequirementRepository.get_requirement_by_id(db, requirement_id)
        if requirement is None:
            raise RequirementNotFoundError()
        if not requirement.extracted_text:
            raise ExtractedTextNotFoundError()
        analysis = json.loads(requirement.analysis_result or "{}")
        quality = json.loads(requirement.quality_result or "{}")
        questions = json.loads(requirement.clarification_questions_result or "{}")
        context = requirement.project.description
        try:
            refactored = GeminiService().refactor_srs(requirement.extracted_text, answers, context)
            quality = GeminiService().check_requirement_quality(json.dumps(refactored, ensure_ascii=False))
            cases_input = "\n\nRefactored and suggested functionality:\n" + json.dumps({
                "functional_requirements": refactored.get("functional_requirements", []),
                "suggested_additions": refactored.get("suggested_additions", []),
            }, ensure_ascii=False)
            test_cases = GeminiService().generate_test_cases(requirement.extracted_text + cases_input)
        except AIProviderUnavailableError as exc:
            report = RequirementService._save_ai_unavailable_draft(
                db, requirement,
                reason=f"{exc.public_summary} Clarification answers were recorded; retry refinement when a provider is available.",
            )
            report["applied_answers"] = answers
            requirement.improvement_report_result = json.dumps(report, ensure_ascii=False)
            db.commit()
            return report
        report = GeminiService.normalize_upload_result(
            source_text=requirement.extracted_text,
            analysis=analysis,
            test_cases=test_cases,
            quality=quality,
            refactored=refactored,
            questions=questions,
        )
        report["document_name"] = requirement.document_name
        report["applied_answers"] = answers
        requirement.refactored_srs_result = json.dumps({"answers": answers, "result": refactored})
        requirement.quality_result = json.dumps(quality)
        requirement.test_cases_result = json.dumps(test_cases)
        requirement.improvement_report_result = json.dumps(report)
        requirement.status = "Analyzed"
        requirement.project.status = "Complete"
        db.commit()
        return report
