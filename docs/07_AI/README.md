# AI

This section documents the AI behavior behind requirements analysis, SRS generation, quality review, test generation, clarification, refactoring, and diagram generation.

## Provider strategy

SpecMind can use local Ollama and hosted NVIDIA, OpenRouter, and Gemini providers. Provider configuration is kept in the ignored `backend/.env`; runtime prompts and orchestration live in `backend/app/ai/`.

AI documentation should record:

- Prompt purpose and expected structured output
- Provider/model assumptions
- Validation and normalization rules
- Failover and cooldown behavior
- Source-based fallback behavior
- Privacy and secret-handling requirements
- Mocking strategy for tests

Do not place API keys, private uploaded documents, or sensitive generated content in this directory.
