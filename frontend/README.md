# Student 4 — frontend and integration

Build the React/TypeScript + Leaflet interface here. Current code is a buildable starter, not the finished interactive map.

```powershell
npm ci
npm run dev
npm run build
```

The development `/api` proxy targets `http://127.0.0.1:8000`. Start the backend separately from the repository root. Add any required frontend variables to an ignored `.env.local`; document names without secrets.

First implement the map, clickable building/group details, before/after crops, category/tier filters, linked building list, summary counts and CSV/GeoJSON downloads against `contracts/examples/result.fixture.json`. That file is explicitly synthetic development data, never evidence of model accuracy. Then replace fixture loading with Student 3's real API.

Own `src/`, frontend configuration/tests and the frontend report in `reports/frontend/`. Agree interface changes with Student 3 in `contracts/` before changing field names. Keep native probabilities distinct from three-category display probabilities. Clearly distinguish reference footprints, synthetic fixtures and actual predictions. Show useful loading/empty/error states.
