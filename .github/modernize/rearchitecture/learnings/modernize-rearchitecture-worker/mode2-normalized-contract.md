# Mode 2 Normalized Contract

Mode 2 should expose one source-preserving normalized artifact instead of making the UI assemble several narrow AI responses.

## What Happened
The existing upload flow persisted extracted text but returned separate analysis, quality, test, refactor, and question payloads with inconsistent shapes. A server-side normalizer now assigns stable IDs, preserves `source_text`, merges diagram sources, and exposes change/suggestion/score fields. Clarification answers are submitted separately and stored with the refactor result.

## Takeaway
Keep the original extracted source immutable in the response contract; apply Q&A only to the improved result. Use deterministic diagram fallbacks so the six-tab UI remains usable when a model omits optional diagram fields.

## History
- 2026-10-09 (SpecMind-AI/mode2-upload-improve): initial
