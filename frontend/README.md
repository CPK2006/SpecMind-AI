# SpecMind AI Frontend

React/Vite interface for the two requirements workflows.

## Run locally

```powershell
npm install
npm run dev
```

The frontend uses `VITE_API_URL` when provided and otherwise connects to `http://localhost:8000/api/v1`.

## User flow

1. Register locally, then sign in.
2. Review previous projects on the dashboard.
3. Create a project using **Pitch an idea** or **Improve an SRS**.
4. View generated SRS/report scores, requirements, issues, test cases, and diagram source.

The local authentication implementation is for the MVP only; it stores demo credentials in browser storage until backend authentication is implemented.
