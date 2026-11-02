# SpecMind AI Frontend

React/Vite single-page workspace for creating, reviewing, improving, and exporting software requirements.

## Stack

- React 18
- Vite 5
- Axios
- Mermaid 12
- CSS-based responsive UI

## Run locally

```powershell
npm install
npm run dev
```

Open `http://localhost:5173`. The app uses `VITE_API_URL` when provided; otherwise it calls `http://localhost:8000/api/v1`.

For a production build:

```powershell
npm run build
npm run preview
```

## Main user flow

1. Register or sign in.
2. Review saved projects on the dashboard.
3. Choose **Pitch an idea** or **Improve an SRS**.
4. Inspect requirements, quality signals, tests, reports, and diagrams.
5. Reopen saved workspaces or export a generated SRS from the backend.

The frontend stores the JWT access token in session storage for the MVP. Production deployments should review token storage, session policy, CORS, and deployment security.

## Tests

```powershell
npm test
```

Diagram behavior tests live in `tests/diagram.test.js`.
