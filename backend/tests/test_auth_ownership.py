
import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.main import app
from app.api.v1.routers.project import get_owned_project
from app.api.v1.routers.requirement import get_owned_requirement
from app.services.project_service import ProjectService


client = TestClient(app)


def make_user(user_id=None):
    return SimpleNamespace(
        id=user_id or uuid.uuid4(),
        email="test@example.com",
        full_name="Test User",
    )


def test_projects_reject_unauthenticated_request():
    response = client.get("/api/v1/projects")

    assert response.status_code == 401


def test_project_detail_rejects_unauthenticated_request():
    response = client.get(
        f"/api/v1/projects/{uuid.uuid4()}"
    )

    assert response.status_code == 401


def test_requirement_analysis_rejects_unauthenticated_request():
    response = client.post(
        f"/api/v1/requirements/{uuid.uuid4()}/analyze"
    )

    assert response.status_code == 401


def test_project_lookup_uses_authenticated_owner(monkeypatch):
    user = make_user()
    project_id = uuid.uuid4()
    observed = {}

    def fake_get_project(db, requested_id, owner_id):
        observed["project_id"] = requested_id
        observed["owner_id"] = owner_id
        return None

    monkeypatch.setattr(
        ProjectService,
        "get_project_by_id",
        fake_get_project,
    )

    with pytest.raises(HTTPException) as exc:
        get_owned_project(None, project_id, user)

    assert exc.value.status_code == 404
    assert observed["project_id"] == project_id
    assert observed["owner_id"] == user.id


def test_project_owned_by_user_is_returned(monkeypatch):
    user = make_user()
    project = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user.id,
    )

    monkeypatch.setattr(
        ProjectService,
        "get_project_by_id",
        lambda db, project_id, owner_id: (
            project
            if project_id == project.id and owner_id == user.id
            else None
        ),
    )

    result = get_owned_project(None, project.id, user)

    assert result is project


def test_unassigned_legacy_project_is_not_returned(monkeypatch):
    user = make_user()
    legacy_project = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=None,
    )

    monkeypatch.setattr(
        ProjectService,
        "get_project_by_id",
        lambda db, project_id, owner_id: None,
    )

    with pytest.raises(HTTPException) as exc:
        get_owned_project(None, legacy_project.id, user)

    assert exc.value.status_code == 404


def test_requirement_owned_by_another_user_is_hidden():
    owner = make_user()
    other_user = make_user()

    requirement = SimpleNamespace(
        id=uuid.uuid4(),
        project=SimpleNamespace(user_id=other_user.id),
    )

    from app.repositories.requirement_repository import RequirementRepository

    original = RequirementRepository.get_requirement_by_id

    try:
        RequirementRepository.get_requirement_by_id = (
            staticmethod(lambda db, requirement_id: requirement)
        )

        with pytest.raises(HTTPException) as exc:
            get_owned_requirement(None, requirement.id, owner)

        assert exc.value.status_code == 404
    finally:
        RequirementRepository.get_requirement_by_id = original


def test_unassigned_project_requirement_is_hidden():
    user = make_user()

    requirement = SimpleNamespace(
        id=uuid.uuid4(),
        project=SimpleNamespace(user_id=None),
    )

    from app.repositories.requirement_repository import RequirementRepository

    original = RequirementRepository.get_requirement_by_id

    try:
        RequirementRepository.get_requirement_by_id = (
            staticmethod(lambda db, requirement_id: requirement)
        )

        with pytest.raises(HTTPException) as exc:
            get_owned_requirement(None, requirement.id, user)

        assert exc.value.status_code == 404
    finally:
        RequirementRepository.get_requirement_by_id = original


def test_requirement_owned_by_user_is_returned():
    user = make_user()

    requirement = SimpleNamespace(
        id=uuid.uuid4(),
        project=SimpleNamespace(user_id=user.id),
    )

    from app.repositories.requirement_repository import RequirementRepository

    original = RequirementRepository.get_requirement_by_id

    try:
        RequirementRepository.get_requirement_by_id = (
            staticmethod(lambda db, requirement_id: requirement)
        )

        result = get_owned_requirement(None, requirement.id, user)

        assert result is requirement
    finally:
        RequirementRepository.get_requirement_by_id = original
