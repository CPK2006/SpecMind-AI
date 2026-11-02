from app.ai.gemini_service import GeminiService


def test_upload_report_keeps_extracted_items_and_refined_content():
    report = GeminiService.normalize_upload_result(
        source_text="Full extracted SRS text",
        analysis={
            "is_software_document": True,
            "functional_requirements": [
                {"id": "FR-001", "title": "Sign in", "description": "Users can sign in", "source_trace": "Section 2"},
                {"id": "FR-002", "title": "Export", "description": "Users can export reports"},
            ],
            "non_functional_requirements": [
                {"id": "NFR-001", "category": "Performance", "description": "Respond in under two seconds"},
            ],
        },
        refactored={
            "title": "Refined SRS",
            "functional_requirements": [
                {"id": "FR-001", "title": "Secure sign in", "description": "Users can sign in securely", "origin": "improved", "acceptance_criteria": ["Invalid credentials are rejected"]},
                {"id": "FR-003", "title": "Password reset", "description": "Users can reset passwords", "origin": "suggested"},
            ],
            "change_summary": {"added": ["FR-003"], "improved": ["FR-001"], "unchanged": [], "removed": []},
        },
        test_cases={"test_cases": [{"id": "TC-001", "requirement_id": "FR-001", "steps": ["Sign in"], "expected_result": "Signed in"}]},
        quality={"quality_score": 82, "confidence_score": 91, "confidence_reasons": ["Source was readable"], "issues": []},
        questions={"questions": [{"id": "Q-001", "question": "Which identity provider?"}]},
    )

    assert report["source_text"] == "Full extracted SRS text"
    assert [item["id"] for item in report["functional_requirements"]] == ["FR-001", "FR-003", "FR-002"]
    assert report["functional_requirements"][0]["source_trace"] == "Section 2"
    assert report["functional_requirements"][1]["origin"] == "suggested"
    assert report["functional_requirements"][2]["origin"] == "extracted"
    assert report["non_functional_requirements"][0]["origin"] == "extracted"
    assert report["test_cases"][0]["requirement_id"] == "FR-001"
    assert all(case.get("requirement_id") in {item["id"] for item in report["functional_requirements"]} for case in report["test_cases"])
    assert not any(case.get("coverage_gap_filled") for case in report["test_cases"])
    assert report["quality_score"] == 58
    assert report["confidence_score"] is None
    assert any("acceptance criteria" in issue for issue in report["quality"]["scoring_basis"]["issues"])
    assert report["change_summary"]["added"] == ["FR-003"]
    assert report["clarification_questions"][0]["id"] == "Q-001"
    assert "architecture_diagram" in report["diagram_sources"]


def test_pitch_test_cases_only_link_real_requirements_and_deduplicate():
    requirements = [
        {"id": "FR-001", "title": "Record book intake", "description": "A librarian records a received book.", "source_trace": "pitch: book intake", "acceptance_criteria": ["The book appears in inventory."]},
        {"id": "FR-002", "title": "Lend a book", "description": "A librarian records a book loan.", "source_trace": "pitch: lending", "acceptance_criteria": ["The loan is recorded against the selected book."]},
    ]
    cases = [
        {"id": "TC-001", "requirement_id": "FR-001", "requirement": "Record book intake", "steps": ["Record a new book"], "expected_result": "The book appears in inventory."},
        {"id": "TC-001", "requirement_id": "FR-001", "requirement": "Record book intake", "steps": ["Record a new book"], "expected_result": "The book appears in inventory."},
        {"id": "TC-003", "requirement_id": "FR-999", "requirement": "Search catalogue", "steps": ["Search the catalogue"], "expected_result": "Matching titles appear."},
    ]

    normalized = GeminiService._normalize_test_cases(cases, requirements)

    assert len(normalized) == 3  # includes one evidence-based case for FR-002's acceptance criterion
    assert normalized[0]["requirement_id"] == "FR-001"
    assert "requirement_id" not in normalized[1]
    assert normalized[1]["requirement"] == "Search catalogue"
    assert normalized[2]["requirement_id"] == "FR-002"
    assert normalized[2]["expected_result"] == requirements[1]["acceptance_criteria"][0]


def test_library_pitch_fixture_preserves_supported_scope_and_reports_unscored_confidence():
    pitch = "A system for managing library operations, including book intake, lending, due-date tracking, returns, and reporting for librarians and school/college management."
    requirements = [
        ("Book intake", "A librarian records books received by the library.", "The book is available in the library inventory."),
        ("Lending", "A librarian records a loan of an available book.", "The loan is associated with the selected book and borrower."),
        ("Due-date tracking", "The system records the due date for each loan.", "The due date is visible on the active loan."),
        ("Returns", "A librarian records returned books.", "The returned book is no longer marked as on loan."),
        ("Reporting", "Management reviews library operation reports.", "The report reflects recorded intake, loans, due dates, and returns."),
    ]
    functional = [
        {"id": f"FR-{index:03d}", "title": title, "description": description, "source_trace": f"pitch: {title.casefold()}", "acceptance_criteria": [criterion], "origin": "generated"}
        for index, (title, description, criterion) in enumerate(requirements, 1)
    ]
    response = {
        "summary": pitch,
        "functional_requirements": functional,
        "non_functional_requirements": [],
        "test_cases": [
            {"id": f"TC-{index:03d}", "requirement_id": f"FR-{index:03d}", "requirement": title, "precondition": "The library system is available.", "steps": [f"Perform {title.casefold()} using valid records."], "expected_result": expected}
            for index, (title, _, expected) in enumerate(requirements, 1)
        ],
        "quality_score": 85,
        "confidence_score": 90,
        "diagram_sources": GeminiService._default_diagrams(),
    }

    result = GeminiService._normalize_pitch_result(response)

    assert len(result["functional_requirements"]) == 5
    assert len(result["test_cases"]) == 5
    assert {case["requirement_id"] for case in result["test_cases"]} == {item["id"] for item in functional}
    assert all("search" not in item["title"].casefold() and "inventory update" not in item["title"].casefold() for item in result["functional_requirements"])
    assert result["quality_score"] == 100
    assert result["confidence_score"] is None
    expected_headers = {
        "class_diagram": "classDiagram",
        "er_diagram": "erDiagram",
        "architecture_diagram": "flowchart",
        "use_case_diagram": "usecase-beta",
        "data_flow_diagram": "flowchart",
        "sequence_diagram": "sequenceDiagram",
    }
    assert {name: source.splitlines()[0].split()[0] for name, source in result["diagram_sources"].items()} == expected_headers


def test_incomplete_draft_is_not_given_optimistic_scores():
    result = GeminiService.draft_srs_from_pitch("Library staff manage book intake and returns.", reason="AI unavailable")

    assert result["generation_status"] == "draft"
    assert result["quality_score"] is None
    assert result["confidence_score"] is None
    assert result["scoring_basis"]["method"] == "not_evaluated"


def test_pitch_diagram_url_uses_real_legacy_source_when_available_and_preserves_unrecoverable_url():
    live_url = "https://mermaid.live/edit#2864ddc6-2578-40f4-83a4-b11711a95e5f"
    real_class_source = "classDiagram\n  class Book\n  class Loan\n  Book ||--o{ Loan : has"
    result = GeminiService._normalize_pitch_result({
        "diagram_sources": {
            "class_diagram": live_url,
            "er_diagram": "erDiagram\n  BOOK ||--o{ LOAN : has",
        },
        "uml_diagram": real_class_source,
        "functional_requirements": [],
    })

    assert result["diagram_sources"]["class_diagram"] == real_class_source
    assert result["diagram_sources"]["er_diagram"].startswith("erDiagram")

    alias_only = GeminiService._normalize_pitch_result({
        "uml_diagram": real_class_source,
        "functional_requirements": [],
    })
    assert alias_only["diagram_sources"]["class_diagram"] == real_class_source

    unrecoverable = GeminiService._normalize_pitch_result({
        "diagram_sources": {"class_diagram": live_url},
        "functional_requirements": [],
    })
    assert unrecoverable["diagram_sources"]["class_diagram"] == live_url


def test_pitch_normalizer_recovers_valid_legacy_alias_fields_and_preserves_mixed_sources():
    source = "classDiagram\n  class Book\n  class Loan\n  Book ||--o{ Loan : has"
    result = GeminiService._normalize_pitch_result({
        "diagram_sources": {
            "class_diagram": "https://mermaid.live/edit#2864ddc6-2578-40f4-83a4-b11711a95e5f",
            "er_diagram": "erDiagram\n  BOOK ||--o{ LOAN : has",
            "architecture_diagram": "flowchart LR\n  Librarian --> Catalog",
        },
        "uml_diagram": source,
        "functional_requirements": [],
    })
    assert result["diagram_sources"]["class_diagram"] == source
    assert result["diagram_sources"]["er_diagram"].startswith("erDiagram")
    assert result["diagram_sources"]["architecture_diagram"].startswith("flowchart")
    assert result["diagram_sources"]["sequence_diagram"] == ""


def test_diagram_validation_rejects_missing_url_wrong_type_and_empty_diagram():
    assert GeminiService.validate_diagram_source("class_diagram", "")[0] is False
    assert GeminiService.validate_diagram_source(
        "class_diagram", "https://mermaid.live/edit#2864ddc6-2578-40f4-83a4-b11711a95e5f"
    )[0] is False
    assert GeminiService.validate_diagram_source("class_diagram", "erDiagram\n  A ||--o{ B : has")[0] is False
    assert GeminiService.validate_diagram_source("class_diagram", "classDiagram")[0] is False
    assert GeminiService.validate_diagram_source("class_diagram", "classDiagram\n  class Book")[0] is True


def test_diagram_repair_changes_only_invalid_sources_and_reports_provider_failures(monkeypatch):
    valid_class = "classDiagram\n  class Book\n  class Loan\n  Book ||--o{ Loan : has"
    original = {
        "title": "Library Administrative Management System",
        "summary": "Book intake, lending, due dates, and reporting.",
        "functional_requirements": [{"id": "FR-001", "title": "Record book intake"}],
        "quality_score": 85,
        "test_cases": [{"id": "TC-001", "requirement_id": "FR-001"}],
        "diagram_sources": {
            "class_diagram": valid_class,
            "er_diagram": "https://mermaid.live/edit#2864ddc6-2578-40f4-83a4-b11711a95e5f",
            "architecture_diagram": "flowchart LR\n  Librarian --> Catalog",
            "use_case_diagram": "usecase-beta\nactor Librarian\nLibrarian --> UC1",
            "data_flow_diagram": "flowchart LR\n  Book --> Report",
            "sequence_diagram": "sequenceDiagram\n  actor Librarian\n  Librarian->>System: Search",
        },
    }
    calls = []

    def fake_generate(self, prompt, **kwargs):
        calls.append(kwargs)
        return {"source": "erDiagram\n  BOOK ||--o{ LOAN : has"}

    monkeypatch.setattr(GeminiService, "_generate_json", fake_generate)
    repaired = GeminiService.repair_diagram_sources(original)

    assert calls == [{"preferred_provider": "ollama", "local_only": True}]
    assert repaired["repaired"] == ["er_diagram"]
    assert repaired["failures"] == {}
    assert repaired["diagram_sources"]["class_diagram"] == valid_class
    for key, value in original.items():
        if key != "diagram_sources":
            assert value == original[key]


def test_diagram_repair_keeps_original_invalid_value_when_generated_source_is_malformed(monkeypatch):
    live_url = "https://mermaid.live/edit#2864ddc6-2578-40f4-83a4-b11711a95e5f"
    monkeypatch.setattr(GeminiService, "_generate_json", lambda *args, **kwargs: {"source": "classDiagram"})
    repaired = GeminiService.repair_diagram_sources({"diagram_sources": {"class_diagram": live_url}})
    assert repaired["diagram_sources"]["class_diagram"] == live_url
    assert "class_diagram" in repaired["failures"]


def test_upload_diagram_url_is_replaced_only_by_a_real_alias_source():
    live_url = "https://mermaid.live/edit#2864ddc6-2578-40f4-83a4-b11711a95e5f"
    real_source = "flowchart LR\n  Librarian --> LibrarySystem --> Database"
    report = GeminiService.normalize_upload_result(
        source_text="Library SRS",
        analysis={"diagram_sources": {"architecture_diagram": live_url}, "architecture_diagram": real_source},
        refactored={},
        test_cases=[],
        quality={},
    )
    assert report["diagram_sources"]["architecture_diagram"] == real_source
