# Mode 1 implementation

Implemented the requested pitch-to-professional-specification experience in place.

## Upstream Artifacts Consumed
- `clarification-answers.md` — preserved React/Vite, FastAPI, existing API behavior, client-local auth, deterministic fallbacks, and no-secret constraints.

## Evidence Mapping
- `clarification-answers.md#F1/F4/F5/F7/F9` → existing React/Vite UI retained, CSS-token styling extended, responsive tabs added, and component state used.
- `clarification-answers.md#B1/B2/B4` → FastAPI route and existing login/dashboard/upload flows preserved.
- `clarification-answers.md#G1/G5` → stable JSON normalization, six diagram fallbacks, export actions, and no secrets added.

## Deliverables
- `backend/app/ai/prompts.py` — professional pitch output contract including domain, stack, requirements, test cases, scores, reasons, issues, and six named diagram sources.
- `backend/app/ai/gemini_service.py` — stable response normalization with backward-compatible legacy diagram mapping and deterministic fallback sources.
- `frontend/src/main.jsx` — five Mode 1 result tabs: Specification Generator, Diagrams, Test Cases, SRS Document, Report; JSON/Markdown download and print/PDF action.
- `frontend/src/styles.css` — tab, document, diagram selector, responsive, and print styling.
- `frontend/package.json` — required smoke-test script.

## Test Results
- Command: `Set-Location frontend; npm test; npm run build`
- Passed: frontend smoke script; Vite production build
- Failed: 0
- Skipped: 0
- Command: `Set-Location backend; .venv/Scripts/python.exe -m compileall -q app`
- Passed: backend compilation
- Failed: 0
- Skipped: 0
- Command: `from app.main import app; app.openapi()`
- Passed: 12 registered routes; generate-SRS route present
- Failed: 0
- Skipped: 0
- Command: `Invoke-WebRequest http://localhost:8000/health` and `/openapi.json`
- Passed: HTTP 200 for both endpoints
- Failed: 0
- Skipped: 0
- Command: `_normalize_pitch_result({'title': 'Demo'})`
- Passed: all six diagram source keys present
- Failed: 0
- Skipped: 0

## Notes
- Mermaid source is displayed as editable source; no additional rendering dependency was introduced.
- Gemini credentials remain sourced from existing settings and are not exposed in the UI or repository.
- No unresolved blockers found.
