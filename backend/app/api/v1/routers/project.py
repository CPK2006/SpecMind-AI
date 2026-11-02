
from __future__ import annotations

import json
import re
import uuid
from io import BytesIO

from docx import Document
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.ai.gemini_service import GeminiService
from app.core.auth_dependencies import get_current_user
from app.database.dependencies import get_db
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.schemas.api_response import APIResponse
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.project_service import ProjectService
from app.services.requirement_service import RequirementService


router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
)


def get_owned_project(
    db: Session,
    project_id: uuid.UUID,
    current_user: User,
):
    """Return a project only when it belongs to the authenticated user."""
    project = ProjectService.get_project_by_id(
        db,
        project_id,
        current_user.id,
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    return project


@router.get(
    "/{project_id}/workspace",
    response_model=APIResponse[dict],
)
def get_project_workspace(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_owned_project(db, project_id, current_user)

    data = {
        "project": {
            "id": str(project.id),
            "name": project.name,
            "description": project.description,
            "creation_mode": project.creation_mode,
            "status": project.status,
            "created_at": (
                project.created_at.isoformat()
                if project.created_at
                else None
            ),
        },
        "result": None,
        "requirement_id": None,
        "document_name": None,
    }

    if project.creation_mode == "pitch":
        data["result"] = (
            json.loads(project.generated_srs_result)
            if project.generated_srs_result
            else None
        )
    else:
        requirement = max(
            project.requirements,
            key=lambda item: item.created_at,
            default=None,
        )

        if requirement:
            data["requirement_id"] = str(requirement.id)
            data["document_name"] = requirement.document_name
            data["result"] = RequirementService.generate_report(
                db,
                requirement.id,
            )

    return APIResponse(
        success=True,
        message="Project workspace retrieved successfully.",
        data=data,
    )


@router.get("/{project_id}/export/docx")
def export_project_docx(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_owned_project(db, project_id, current_user)

    if project.creation_mode == "pitch":
        payload = (
            json.loads(project.generated_srs_result)
            if project.generated_srs_result
            else None
        )
    else:
        requirement = max(
            project.requirements,
            key=lambda item: item.created_at,
            default=None,
        )
        payload = (
            RequirementService.generate_report(db, requirement.id)
            if requirement
            else None
        )

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Generate the project results before exporting the SRS.",
        )

    document = Document()
    document.add_heading(payload.get("title") or project.name, 0)
    document.add_paragraph(
        payload.get("summary") or "Software Requirements Specification"
    )

    def add_items(heading: str, items: list):
        document.add_heading(heading, level=1)

        if not items:
            document.add_paragraph("None specified.")
            return

        for item in items:
            if isinstance(item, str):
                document.add_paragraph(item, style="List Bullet")
                continue

            if heading == "Test cases":
                case_heading = (
                    f"{item.get('id', 'Test case')} — "
                    f"{item.get('requirement_id') or item.get('requirement') or 'Requirement'}"
                )
                document.add_paragraph(case_heading, style="List Bullet")

                if item.get("precondition"):
                    document.add_paragraph(
                        f"Precondition: {item['precondition']}"
                    )

                for step in item.get("steps") or []:
                    document.add_paragraph(str(step), style="List Bullet 2")

                if item.get("expected_result"):
                    document.add_paragraph(
                        f"Expected result: {item['expected_result']}"
                    )

                continue

            title = item.get("id", "")

            if item.get("title"):
                title += f" {item['title']}"

            detail = (
                item.get("description")
                or item.get("story")
                or item.get("risk")
                or item.get("reason")
                or item.get("requirement")
                or item.get("suggestion")
                or ""
            )

            if item.get("severity"):
                detail = f"{item['severity']}: {detail}"

            document.add_paragraph(
                f"{title}: {detail}" if title else str(detail),
                style="List Bullet",
            )

            if item.get("suggestion") and detail != item.get("suggestion"):
                document.add_paragraph(
                    f"Suggestion: {item['suggestion']}"
                )

            for criterion in item.get("acceptance_criteria") or []:
                document.add_paragraph(
                    str(criterion),
                    style="List Bullet 2",
                )

            if item.get("source_trace"):
                document.add_paragraph(
                    f"Source: {item['source_trace']}",
                    style="Caption",
                )

            if item.get("origin"):
                document.add_paragraph(
                    f"Origin: {item['origin']}",
                    style="Caption",
                )

    add_items(
        "Functional requirements",
        payload.get("functional_requirements") or [],
    )
    add_items(
        "Non-functional requirements",
        payload.get("non_functional_requirements") or [],
    )
    add_items("User stories", payload.get("user_stories") or [])
    add_items("Actors", payload.get("actors") or [])
    add_items("Risks", payload.get("risks") or [])
    add_items("Assumptions", payload.get("assumptions") or [])
    add_items(
        "Missing requirements",
        payload.get("missing_requirements") or [],
    )
    add_items(
        "Suggested additions",
        payload.get("suggested_additions")
        or payload.get("suggestions")
        or [],
    )
    add_items("Test cases", payload.get("test_cases") or [])

    if payload.get("diagram_sources"):
        document.add_heading("Diagrams", level=1)

        for name, source in payload["diagram_sources"].items():
            document.add_heading(name.replace("_", " ").title(), level=2)
            document.add_paragraph(str(source))

    if project.creation_mode == "upload" and payload.get("source_text"):
        document.add_heading("Original extracted source", level=1)
        document.add_paragraph(payload["source_text"])

    if (
        payload.get("quality_score") is not None
        or payload.get("confidence_score") is not None
    ):
        document.add_heading("Quality review", level=1)
        document.add_paragraph(
            f"Quality score: {payload.get('quality_score', 'Not available')} / 100"
        )
        document.add_paragraph(
            f"Confidence score: {payload.get('confidence_score', 'Not available')} / 100"
        )

        add_items(
            "Quality issues",
            (payload.get("quality") or {}).get("issues")
            or payload.get("confidence_issues")
            or [],
        )
        add_items(
            "Confidence reasons",
            payload.get("confidence_reasons") or [],
        )

    if payload.get("change_summary"):
        document.add_heading("Change summary", level=1)

        for change_type, changes in payload["change_summary"].items():
            add_items(change_type.title(), changes or [])

    stream = BytesIO()
    document.save(stream)
    stream.seek(0)

    safe_name = (
        re.sub(r"[^A-Za-z0-9_-]+", "-", project.name).strip("-")
        or "project"
    )
    filename = f"{safe_name}-srs.docx"

    return StreamingResponse(
        stream,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


@router.post(
    "/{project_id}/generate-srs",
    response_model=APIResponse[dict],
)
def generate_srs(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_owned_project(db, project_id, current_user)

    if project.creation_mode != "pitch" or not project.idea_pitch:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This project does not contain an idea pitch.",
        )

    result = GeminiService().generate_srs_from_pitch(
        project.idea_pitch,
        project.description,
    )

    if result.get("generation_status") == "draft":
        result["title"] = f"{project.name} — Draft SRS"

    ProjectRepository.save_generated_srs(
        db,
        project,
        json.dumps(result),
    )

    return APIResponse(
        success=True,
        message="SRS generated successfully.",
        data=result,
    )


@router.post(
    "/{project_id}/diagrams/repair",
    response_model=APIResponse[dict],
)
def repair_project_diagrams(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Repair invalid diagrams in a saved pitch result without regenerating its SRS."""
    project = get_owned_project(db, project_id, current_user)
    if project.creation_mode != "pitch" or not project.generated_srs_result:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This project has no saved pitch SRS to repair.",
        )
    try:
        result = json.loads(project.generated_srs_result)
    except (TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The saved SRS result is not valid JSON and cannot be repaired.",
        ) from exc
    if not isinstance(result, dict):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The saved SRS result has an unsupported structure.",
        )

    repaired = GeminiService.repair_diagram_sources(result)
    result["diagram_sources"] = repaired["diagram_sources"]
    if repaired["failures"]:
        result["diagram_generation_issues"] = repaired["failures"]
        result["generation_status"] = "draft"
        result["generation_note"] = "Some diagrams could not be repaired. See diagram generation issues for details."
    else:
        result.pop("diagram_generation_issues", None)
        if result.get("generation_status") == "draft" and result.get("generation_note", "").startswith("Some diagrams could not be"):
            result.pop("generation_note", None)

    ProjectRepository.save_generated_srs(db, project, json.dumps(result))
    return APIResponse(
        success=True,
        message="Diagram repair completed.",
        data={
            "result": result,
            "repaired_diagrams": repaired["repaired"],
            "failures": repaired["failures"],
        },
    )


@router.post(
    "",
    response_model=APIResponse[ProjectResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = ProjectService.create_project(
            db,
            project,
            current_user.id,
        )

        return APIResponse[ProjectResponse](
            success=True,
            message="Project created successfully.",
            data=ProjectResponse.model_validate(result),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=APIResponse[list[ProjectResponse]],
)
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = ProjectService.list_projects(db, current_user.id)

    return APIResponse[list[ProjectResponse]](
        success=True,
        message="Projects retrieved successfully.",
        data=[
            ProjectResponse.model_validate(project)
            for project in result
        ],
    )


@router.get(
    "/{project_id}",
    response_model=APIResponse[ProjectResponse],
)
def get_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_owned_project(db, project_id, current_user)

    return APIResponse(
        success=True,
        message="Project retrieved successfully.",
        data=project,
    )


@router.put(
    "/{project_id}",
    response_model=APIResponse[ProjectResponse],
)
def update_project(
    project_id: uuid.UUID,
    project: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_project = get_owned_project(db, project_id, current_user)

    result = ProjectService.update_project(
        db,
        db_project,
        project,
    )

    return APIResponse[ProjectResponse](
        success=True,
        message="Project updated successfully.",
        data=ProjectResponse.model_validate(result),
    )


@router.delete(
    "/{project_id}",
    response_model=APIResponse[None],
)
def delete_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_project = get_owned_project(db, project_id, current_user)

    ProjectService.delete_project(db, db_project)

    return APIResponse(
        success=True,
        message="Project deleted successfully.",
        data=None,
    )
