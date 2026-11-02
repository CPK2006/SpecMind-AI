import uuid
from io import BytesIO
from types import SimpleNamespace

from fastapi import UploadFile

from app.repositories.project_repository import ProjectRepository
from app.repositories.requirement_repository import RequirementRepository
from app.services import requirement_service
from app.services.requirement_service import RequirementService


def test_upload_requirement_scopes_project_lookup_to_owner(monkeypatch):
    project_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    observed = {}

    def get_project(db, requested_project_id, requested_owner_id):
        observed["project"] = (requested_project_id, requested_owner_id)
        return SimpleNamespace(id=project_id)

    def create_requirement(db, requirement):
        observed["requirement"] = requirement
        return requirement

    monkeypatch.setattr(ProjectRepository, "get_project_by_id", staticmethod(get_project))
    monkeypatch.setattr(RequirementRepository, "create_requirement", staticmethod(create_requirement))
    monkeypatch.setattr(
        requirement_service,
        "Requirement",
        lambda **values: SimpleNamespace(**values),
    )
    monkeypatch.setattr(
        requirement_service,
        "save_uploaded_file",
        lambda file: (file.filename, "unused-test-path"),
    )
    monkeypatch.setattr(requirement_service, "extract_text", lambda path: "sample SRS")

    result = RequirementService.upload_requirement(
        db=None,
        project_id=project_id,
        owner_id=owner_id,
        title="Sample requirements",
        description=None,
        file=UploadFile(filename="sample.pdf", file=BytesIO(b"test")),
    )

    assert observed["project"] == (project_id, owner_id)
    assert result is observed["requirement"]
    assert result.project_id == project_id
