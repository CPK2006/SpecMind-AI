import json
import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1.routers import project as project_router


def test_repair_endpoint_uses_owner_guard_and_persists_only_diagram_changes(monkeypatch):
    project_id = uuid.uuid4()
    user = SimpleNamespace(id=uuid.uuid4())
    saved = {
        "title": "Library Administrative Management System",
        "summary": "Book intake and lending.",
        "functional_requirements": [{"id": "FR-001", "title": "Record intake"}],
        "quality_score": 85,
        "test_cases": [{"id": "TC-001", "requirement_id": "FR-001"}],
        "diagram_sources": {
            "class_diagram": "https://mermaid.live/edit#2864ddc6-2578-40f4-83a4-b11711a95e5f"
        },
    }
    project = SimpleNamespace(
        id=project_id,
        creation_mode="pitch",
        generated_srs_result=json.dumps(saved),
    )
    owner_checks = []
    persistence = []

    def get_owned(db, requested_id, current_user):
        owner_checks.append((db, requested_id, current_user))
        return project

    monkeypatch.setattr(project_router, "get_owned_project", get_owned)
    monkeypatch.setattr(
        project_router.GeminiService,
        "repair_diagram_sources",
        staticmethod(lambda result: {
            "diagram_sources": {"class_diagram": "classDiagram\n  class Book"},
            "failures": {},
            "repaired": ["class_diagram"],
        }),
    )
    monkeypatch.setattr(
        project_router.ProjectRepository,
        "save_generated_srs",
        staticmethod(lambda db, target, result: persistence.append((target, json.loads(result)))),
    )

    response = project_router.repair_project_diagrams(project_id, db="db", current_user=user)

    assert owner_checks == [("db", project_id, user)]
    assert persistence[0][0] is project
    updated = persistence[0][1]
    for field in ("title", "summary", "functional_requirements", "quality_score", "test_cases"):
        assert updated[field] == saved[field]
    assert response.data["repaired_diagrams"] == ["class_diagram"]


def test_repair_endpoint_does_not_run_provider_or_save_when_owner_check_rejects(monkeypatch):
    invoked = []

    def denied(*args):
        raise HTTPException(status_code=404, detail="Project not found.")

    monkeypatch.setattr(project_router, "get_owned_project", denied)
    monkeypatch.setattr(
        project_router.GeminiService,
        "repair_diagram_sources",
        staticmethod(lambda result: invoked.append("provider")),
    )
    monkeypatch.setattr(
        project_router.ProjectRepository,
        "save_generated_srs",
        staticmethod(lambda *args: invoked.append("save")),
    )

    with pytest.raises(HTTPException) as error:
        project_router.repair_project_diagrams(uuid.uuid4(), db=None, current_user=None)

    assert error.value.status_code == 404
    assert invoked == []
