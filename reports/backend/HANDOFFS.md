# Student 3 status and teammate handoffs

Implementation evidence from 23 November 2026; handoff refreshed on 26 November 2026 on `codex/student3-backend-handoff`. Local datasets, runtime artifacts and checkpoints stay outside Git. The code and examples are available for teammate review; integration approval has not been assumed.

## Completed locally

- FastAPI routes for prepared examples, uploads, serial jobs, status, results, previews and whole-job downloads.
- SQLite persistence, exclusive worker ownership, failed/empty-result handling and restart behavior.
- Geographic checks, probability grouping and consistent API/CSV/GeoJSON records.
- Request/status/inference examples and a documented provider interface in `contracts/API.md`.
- All 40 source/backend tests passed, including 23 backend cases, plus a reproducible local imagery validation command and full-registry startup/readiness smoke check.
- A Student 3 report draft in this directory.

## Remaining milestones

| Gate | Remaining evidence | Dependency |
|---|---|---|
| Interface review | Confirm request/output fields and whole-job download labels | Students 2 and 4 |
| Imagery/preprocessing review | Confirm sidecars, provenance and existing black edge padding | Students 1 and 2 |
| Genuine inference | Complete trained provider, verified checkpoint, actual prepared and uploaded jobs | Student 2 |
| Frontend integration | Map, linked list, previews, status/error feedback and matching downloads | Student 4 |
| Reproducibility | Run one genuine completed job on another laptop and record commands/artifacts | Team |
| Final report | Insert actual model/job identity, screenshots and completed integration results | Students 1, 2 and 4 |

## Message for Student 1

I have implemented the backend input registry, pair validation, geographic conversion and consistent exports. The local registry accepts 12 prepared Haiti pairs and 1,178 xBD pairs. It excludes 162 xBD pairs whose geographic transforms failed or are unavailable. The audit command is `python scripts/verify_backend.py --output runtime/backend_validation.json`.

Please review the accepted imagery/sidecar provenance and provide the preparation checks that support using these pairs. I also found that the current crop helper uses black padding outside image bounds, while the team plan says edge padding. Please agree the intended behavior with Student 2 before genuine inference integration. Send the relevant preparation/limitations evidence for my geographic validation report. My independent backend tests and documentation can proceed while you review.

## Message for Student 2

I have implemented the serial job API, geographic results, crop previews and exports. `contracts/API.md` documents the imagery-only pair passed to your provider and the required output, with a synthetic shape example in `contracts/examples/inference.output.fixture.json`.

Please supply a callable provider with `check_ready()` and `__call__(pair)`, a reloadable trained paired checkpoint with checksum/model identity, confirmed four-class order, preprocessing and runtime requirements. Your function should own thresholding, connected-region/polygon extraction and classification, returning unique region IDs, pixel polygons, probabilities, object kind and crop windows. The existing detector currently returns a probability raster, so polygon extraction still needs your implementation. Verify the existing black crop-padding behavior with Student 1.

The server enables inference through `QUAKE_INFERENCE=package.module:provider`. Until your provider is available, health reports inference unavailable and real job submissions return 503. This blocks the genuine prepared/uploaded-pair integration gate. Backend behavior is already testable with controlled test inference.

## Message for Student 4

The backend routes and examples are ready for integration review. Please review `contracts/API.md` and `docs/INTEGRATION_HANDOFF.md`; the latter records the current frontend/client differences and proposed acceptance checks. Prepared submissions use JSON with `input_type=prepared` and a pair ID from `/pairs`. Uploads use multipart `input_type=upload` and `before`/`after` files. Poll job status, then load the result envelope from `/jobs/{job_id}/buildings` and follow its crop URLs. Prefix backend URLs with `/api` through the Vite proxy.

Downloads cover the whole completed job, so please label them “Download whole job” and show the total separately from filtered counts. Use the agreed `destroyed` display-category wire name. The existing synthetic fixture is available for UI work. Genuine submissions return 503 until Student 2's provider is configured. Please integrate loading/empty/failure states and later send screenshots and evidence that map/list IDs, counts, crop previews and both downloads agree for one real job.

## Integration evidence to record

After Student 2's provider arrives, record the provider target, trained checkpoint checksum, pair IDs, submission commands, completed job IDs and model version. With Student 4, record map/download ID and count checks, screenshots, one empty/error flow and one uploaded-pair flow. Repeat a genuine job on a second laptop. Update the report with the observed evidence.
