# Frontend/backend handoff and integration review

Review date: 26 November 2026. Compared GitHub `main` at `46b47b7` with the preserved, uncommitted Student 3 backend. This is a proposed agreement and observed gap list, not teammate approval. This document accompanies the Student 3 backend handoff branch; teammate acceptance remains pending.

## What exists

Student 4 has delivered source for a Leaflet map, linked tier-sorted list, category/tier filters, region details, a visibly marked synthetic fixture, and live-job controls. GitHub's final backend remains the health-only starter: an intermediate backend implementation was subsequently reverted. This handoff branch supplies Student 3's full backend and expanded API documentation for review; they are not yet merged into main.

The four AI role guides explain responsibilities and context. They do not replace the shared API specification, a reviewed implementation, or integration evidence. The published API draft already specifies the buildings and exports routes; the new client uses different routes. Upload fields were still unspecified in the published draft, so those required coordination rather than independent assumptions.

## Proposed working agreement

1. Students 3 and 4 review `contracts/API.md` and its examples together. Use the local implemented contract below as the proposed baseline; record explicit acceptance or revisions in a pull request. Student 2 reviews provider and probability semantics. No approval is implied by this document.
2. Student 3 publishes the backend, examples, tests and API specification in one reviewable PR. Student 4 aligns the client, types and UI with the accepted contract in a frontend PR. Keep responsibility for each module with its owner.
3. Change a shared request/response only with the specification, example and affected client/server changes in the same coordinated PR or linked PRs. State compatibility and merge order.
4. Both students review the integration evidence below. Build success alone does not establish compatibility. Controlled test predictions must remain separate from genuine trained inference.
5. Record acceptance with actual GitHub handles, PR links, reviewed commit SHAs, date, checks and unresolved limitations. Use branches and reviewed PRs for subsequent work; avoid direct updates to shared main.

## Observed mismatches and proposed baseline

| Operation | Current frontend | Local backend / proposed contract | Owner of next action |
|---|---|---|---|
| Prepared-pair listing | Expects a bare array with a required `label`; silently retains an invented fallback ID on failure | `GET /pairs` returns `{pairs: [...], rejected: ...}`; records contain `pair_id`, dimensions, CRS and provenance | Student 4 unwraps `pairs`, labels with `pair_id` or an agreed optional label, and shows empty/error states without invented live choices |
| Prepared submission | Sends `{pair_id}` | `POST /jobs` JSON requires `{input_type: "prepared", pair_id}` | Student 4 updates request |
| Upload | Posts to `/jobs/upload`, fields `before_image`, `after_image`, optional `pair_id` | `POST /jobs`, exactly `input_type=upload`, `before`, `after` | Student 4 updates route/fields and removes unsupported pair-label submission |
| Completed results | `/jobs/{id}/result` | `/jobs/{id}/buildings` returns the result envelope | Student 4 updates route |
| Downloads | `/jobs/{id}/export.csv` and `.geojson` | `/jobs/{id}/exports/csv` and `/exports/geojson` | Student 4 updates URLs |
| Crop previews | Flat `before_crop_url` / `after_crop_url`; raw image URL | `properties.crop_urls.before` / `.after`; root-relative URLs need `/api` through Vite | Student 4 updates types, preview reads and URL resolution |
| Export scope | Generic “Export Report” with visible filtered counts | Downloads cover the whole completed job | Student 4 labels “Download whole job” and displays total separately from visible counts |
| No loaded live result | Live mode keeps displaying a marked synthetic fixture | Proposed UI: explicit “No live assessment loaded”; fixture shown only in fixture mode | Students 3/4 confirm expected behavior; Student 4 implements |
| Fresh installation | `package.json` adds `concurrently`; lockfile has no corresponding entry | Setup and CI use `npm ci` | Student 4 removes unused dependency or updates lockfile with intentional dependency change |
| Development commands | `.venv/bin/python` and `bash` in new combined startup scripts | Documented Windows environment uses `.venv/Scripts/python.exe` and PowerShell | Student 4 documents supported platforms or supplies portable scripts; separate terminals remain available |

Keep four native classes, grouped display probabilities, backend-provided geography, stable region IDs and within-tier ties. These concepts already align in the frontend source. A copy of the shared fixture now also exists under `frontend/src/data/`; keep it synchronized or explicitly document any additional synthetic scenarios.

## Acceptance evidence

| Check | Required evidence | Reviewers |
|---|---|---|
| Fresh setup | Clean checkout installs with `npm ci` and builds; documented backend startup works on the target laptop | Students 3/4 |
| Fixture interaction | Map/list selection, filters, counts, legend and clear synthetic labeling; screenshots and observed interactions | Student 4, reviewed by Student 3 |
| API compatibility | Actual HTTP requests verify pair listing, prepared submission, upload, polling, result envelope, crop URLs and both exports | Students 3/4 |
| Error/empty handling | Unavailable inference (503), invalid input (422), failed job, no detections, pair-list failure and missing crops produce accurate UI states | Students 3/4 |
| Scope consistency | Same job/region IDs across unfiltered results, CSV and GeoJSON; filtered map/list/visible counts match; downloads visibly cover whole job | Students 3/4 |
| Genuine inference | Student 2 supplies ready provider and trained checkpoint identity; record real prepared and uploaded jobs, model identity and preview evidence | Students 2/3/4 |
| Reproducibility | Repeat a genuine job on a second laptop and record setup and results | Team |

A controlled provider can verify API plumbing before training, with evidence explicitly labeled as a test. It cannot satisfy the genuine-inference gate. Backend absence/readiness must never be hidden by pretending a fixture is a completed live job.

## Acceptance record to complete in review

Checks performed during this review:

- Frontend build: `npm run build` passed using existing local dependencies. No browser interaction verification was performed.
- Fresh-install dependency check: `npm ci --dry-run --ignore-scripts --no-audit --no-fund --fetch-retries=0` failed because `package.json` and `package-lock.json` are out of sync (`concurrently` and transitive dependencies missing). This prevents the documented clean-install path until corrected.
- Full Python suite: 40 tests passed; repository source check passed.
- Local backend: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` with `.venv/Scripts/python.exe -m pytest tests/test_backend.py -q` passed all 23 tests. This verifies controlled backend cases, not genuine model or browser integration.
- GitHub PR search returned no pull requests at review time. Only `origin/main` was advertised by the configured branch fetch. Unpushed work is not visible in this review.

- Student 3 / GitHub handle: pending
- Student 4 / GitHub handle: pending
- Student 2 provider/semantics review: pending
- Backend branch: `codex/student3-backend-handoff`; PR and reviewed commit to be recorded during review
- Frontend PR and commit: pending
- Agreed contract version and examples: pending
- Verification commands, outcomes and interaction evidence: pending
- Remaining blockers and accepted limitations: pending

See `reports/backend/HANDOFFS.md` for the existing backend handoff and `docs/OWNERSHIP.md` for role ownership. The crop-padding discrepancy between the team plan and existing preprocessing still requires Students 1/2 review before trained model integration.
