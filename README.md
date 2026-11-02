g# SpecMind AI

AI-powered Requirements Intelligence Platform

---

## Vision

Engineering Begins with Better Requirements.

---

## Problem

Existing AI tools generate text.

Existing enterprise tools manage requirements.

SpecMind AI bridges the gap by understanding, validating, improving, and tracing software requirements.

---

## Features

- AI Business Analyst
- Requirement Intelligence
- Requirement Quality
- Hidden Requirement Detection
- Traceability
- Engineering Knowledge Graph
- UML Generation
- Sprint Planning
- Test Generation
- Risk Analysis

---

## Workflows

### Pitch an idea

Create a project with an idea and context. SpecMind sends the pitch to the AI requirements pipeline and returns a structured SRS containing requirements, user stories, acceptance criteria, test cases, quality/confidence scores, and Mermaid-compatible UML/architecture diagram source.

The results workspace includes specification, diagram, test case, assembled SRS, and quality report tabs. SRS exports include DOCX, Markdown, JSON, and browser print-to-PDF.

### Improve an existing SRS

Upload a PDF or DOCX. SpecMind extracts the text, analyzes requirements, generates test cases, reviews quality, and returns a combined improvement report. The original uploaded document remains unchanged.

The improvement workspace includes extracted and refined requirements, clarification questions, selectable use cases, rendered Mermaid diagrams with source, linked tests, a refactored SRS, and a change and quality report. Answering questions regenerates and saves the complete updated workspace. Projects can be reopened from the dashboard.

## Run locally

Start PostgreSQL, configure `backend/.env` from `backend/.env.example`, then run the backend and frontend in separate terminals. The backend API is at `http://localhost:8000` and the frontend is at `http://localhost:5173`.

The current authentication is an MVP browser-local flow and must be replaced by server-side authentication before production deployment.

---

## Technology

AI requests use NVIDIA, OpenRouter, then Gemini, with Gemini key rotation. Configure provider credentials in the ignored `backend/.env`; see `backend/README.md` for setup. OpenRouter's low cost tier is a preference rather than a spending limit.

React

FastAPI

PostgreSQL

Gemini

Docker

---

## License

MIT
