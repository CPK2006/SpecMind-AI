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
    covered = {case["requirement_id"] for case in report["test_cases"]}
    assert {item["id"] for item in report["functional_requirements"]} <= covered
    assert any(case.get("coverage_gap_filled") for case in report["test_cases"])
    assert report["quality_score"] == 82
    assert report["confidence_score"] == 91
    assert report["change_summary"]["added"] == ["FR-003"]
    assert report["clarification_questions"][0]["id"] == "Q-001"
    assert "architecture_diagram" in report["diagram_sources"]
