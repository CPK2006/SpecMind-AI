# SpecMind AI: Two-Mode Workflows

## Pitch an idea

The user supplies a project name, context, and idea pitch. The system creates a `pitch` project and generates a structured SRS with requirements, actors, user stories, acceptance criteria, test cases, risks, quality score, confidence score, and diagram source.

## Improve an existing SRS

The user supplies a project name, context, and PDF/DOCX SRS. The system stores the original document, extracts its text, analyzes requirements, generates test cases, reviews quality, and returns improvement findings. Future refactoring and clarification iterations must create new versions rather than overwrite the original.

## MVP boundaries

- Authentication is currently browser-local and not production-safe.
- Gemini is the active AI provider.
- Uploads are limited to PDF and DOCX and are stored locally.
- Reports are currently returned through the API and displayed in the frontend; durable report/artifact versioning is the next persistence increment.