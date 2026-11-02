# Optional Clarification Answer Serialization

Gemini refactoring should accept optional mapping answers without changing the legacy one-argument call path.

## What Happened
For SpecMind-AI Mode 2, the clarification route supplied a second argument while existing refactor callers supplied only the document. The service now copies and serializes an optional mapping, and the prompt explicitly distinguishes supplied answers from the empty-answer path.

## Takeaway
Use `Mapping[str, str] | None`, serialize a copied mapping, and instruct the model to apply every supplied answer without overwriting immutable source text.

## History
- 2026-10-09 (SpecMind-AI/mode2-clarification-answer-contract): initial
