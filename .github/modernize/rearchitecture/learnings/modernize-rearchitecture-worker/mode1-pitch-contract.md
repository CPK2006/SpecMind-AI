# Mode 1 pitch contract

The pitch workflow uses a normalized JSON contract so model revisions and legacy responses remain UI-compatible.

## What Happened
The professional Mode 1 UI needs six selectable diagram sources and separate score/reason sections. The backend prompt now requests those fields explicitly; `GeminiService._normalize_pitch_result` maps legacy `uml_diagram`/`architecture_diagram` fields and supplies deterministic Mermaid fallbacks.

## Takeaway
Keep AI output normalization at the service boundary. Frontend tabs can then consume stable fields without coupling rendering to a specific model response version or adding a diagram-rendering dependency.

## History
- 2026-10-09 (SpecMind-AI/mode1): initial
