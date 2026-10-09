# Mode 2 Clarification Answer Contract

Updated the Gemini refactor path so optional clarification answers are incorporated into the prompt while preserving existing one-argument calls.

## Upstream Artifacts Consumed
- `rearchitecture/learnings/modernize-rearchitecture-worker/mode2-normalized-contract.md` — preserved immutable source text and applied answers only to the improved SRS.
- No context, board, decisions, or task-breakdown artifacts were present in the workspace.

## Evidence Mapping
- `mode2-normalized-contract.md` → `backend/app/ai/gemini_service.py:refactor_srs` serializes optional answers and retains source-only behavior when absent.
- `mode2-normalized-contract.md` → `backend/app/ai/prompts.py:REFACTOR_SRS_PROMPT` explicitly applies answers to improved requirements without overwriting source text.

## Changes
- `GeminiService.refactor_srs` now accepts `Mapping[str, str] | None`, copies and pretty-serializes supplied answers, and keeps `refactor_srs(document)` compatible.
- `REFACTOR_SRS_PROMPT` now defines the answers object as optional, requires each supplied answer to be applied where relevant, and defines `{}` as the no-answer path.

## Test Results
- Command: backend `compileall` plus isolated prompt-contract assertions and OpenAPI schema inspection
- Passed: compile, one-argument refactor contract, answered refactor contract, clarification route presence
- Failed: 0
- Skipped: 0
- Command: `npm run build` from `frontend`
- Passed: Vite production build (85 modules transformed)
- Failed: 0
- Skipped: 0

## Risks
- Gemini behavior remains model-dependent at runtime; prompt construction now carries the answers deterministically and explicitly.
