## mode1 — professional pitch experience
- Codebase/domain discoveries: pitch generation already persisted opaque JSON and the UI had a single report; upload mode uses separate analysis/report flows.
- Wrong assumptions and corrections: the first targeted replacement accidentally normalized document analysis; corrected it so only pitch generation is normalized.
- Debugging dead-ends and what actually worked: terminal cwd persisted from frontend, so backend verification required absolute `Set-Location`.
- Techniques/patterns worth reusing: normalize AI contracts server-side; use component-state tabs to avoid adding dependencies; retain source text for Mermaid export/editing.
- Learnings consumed: none

## mode2 — upload/improve workspace
- Codebase/domain discoveries: Mode 2 already extracted and persisted source text, but the API split analysis into narrow contracts and lacked answer submission.
- Wrong assumptions and corrections: the legacy report schemas expected string-only requirements; route response wrappers were relaxed to support structured traceable items.
- Debugging dead-ends and what actually worked: pytest is unavailable in the backend venv, while compileall, OpenAPI generation, frontend build, and normalizer smoke checks pass.
- Techniques/patterns worth reusing: normalize model drift server-side and preserve immutable source text while applying clarification answers only to refactored output.
- Learnings consumed: none

## 2026-10-09 mode2-clarification-answer-contract — optional Gemini clarification answers
- Codebase/domain discoveries: the route already passed `payload.answers`; the service and prompt needed an explicit optional contract.
- Wrong assumptions and corrections: initial validation ran npm from the backend cwd and asserted the wrong empty-JSON formatting; rerunning from `frontend` and checking semantic prompt text resolved both issues.
- Debugging dead-ends and what actually worked: backend compile/OpenAPI plus an isolated stubbed Gemini prompt check provided deterministic coverage without an API call.
- Techniques/patterns worth reusing: accept `Mapping[str, str] | None`, serialize a copied mapping, and preserve the one-argument call path.
- Learnings consumed: [modernize-rearchitecture-worker/mode2-normalized-contract]
