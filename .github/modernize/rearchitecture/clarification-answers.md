---
schema: clarification-answers/v1
status: submitted
generated_at: "2026-10-09T02:15:35.174Z"
scope: [frontend, backend, generic]
questions_file: clarification-questions.json
---

# Rearchitecture Clarification Answers

## 🖥️ Frontend

- **F1** Which frontend framework and version should the completed implementation target?
  - answer: React/Vite existing frontend
  - source: user
- **F2** Which component or UI library should the frontend use for the completed flows?
  - answer: _none_
  - source: skipped (required, no default — blocking gap)
- **F3** What screenshots, recordings, staging URLs, or other visual references define the current UI and required states?
  - answer: _none_
  - source: skipped (required, no default — blocking gap)
- **F4** What design system, token source, or visual fidelity rule should govern the completed frontend?
  - answer: match existing pixel-by-pixel using extracted CSS custom properties
  - source: user
- **F5** Which accessibility standard should the completed frontend target?
  - answer: WCAG 2.1 AA
  - source: user
- **F6** Which browsers and runtime targets must the completed frontend support?
  - answer: modern evergreen (Chrome, Firefox, Safari, Edge — latest 2 major versions)
  - source: default applied
- **F7** What responsive and breakpoint strategy should the completed product use?
  - answer: mobile-first using existing breakpoints detected from codebase
  - source: user
- **F8** Which locales and internationalization behavior are in scope?
  - answer: preserve current locales; keep existing i18n library if present
  - source: default applied
- **F9** What client-side state management strategy should be used?
  - answer: preserve existing pattern if identifiable; otherwise recommend minimal (component state + server-state library)
  - source: user
- **F10** Which routing library or URL-preservation strategy should the frontend use?
  - answer: use the de-facto router for the chosen target framework
  - source: user

## ⚙️ Backend

- **B1** Which backend framework and version should the completed implementation target?
  - answer: FastAPI existing backend
  - source: user
- **B2** How should existing API routes, payloads, and status-code behavior be handled while completing the backlog?
  - answer: must preserve
  - source: user
- **B3** What data and persistence strategy should be used for the existing PostgreSQL data and new SRS/workflow artifacts?
  - answer: persistence or coherent JSON artifact persistence; PostgreSQL/Alembic already present
  - source: user
- **B4** What authentication and authorization behavior should the completed product provide?
  - answer: Authentication can remain client-local but document it
  - source: user
- **B5** What latency, throughput, availability, or AI workflow completion targets should be treated as acceptance criteria?
  - answer: match current production baseline; no regression
  - source: default applied

## 📋 General

- **G1** What exact outcome defines completion of the remaining SpecMind AI backlog?
  - answer: All remaining todos implemented for both Pitch and Upload/improve modes, with stable schemas, workflows, exports, safe persistence/parsing, docs, tests, and no secret exposure
  - source: user
- **G2** What components, behaviors, integrations, or product changes must not be modified?
  - answer: No explicit exclusions beyond keeping authentication client-local and following the existing stack
  - source: user
- **G3** How should the existing tests be treated while completing the backlog?
  - answer: must pass
  - source: user
- **G4** Where should the completed implementation be written for this brownfield rewrite?
  - answer: d:\Projects\SpecMind-AI (existing repository, in place)
  - source: user
- **G5** What additional requirements, exclusions, dependencies, compliance rules, or operational constraints should govern implementation?
  - answer: No secret exposure; deterministic fallbacks; preserve uploaded originals; document client-local authentication; complete all remaining todos before stopping.
  - source: user
