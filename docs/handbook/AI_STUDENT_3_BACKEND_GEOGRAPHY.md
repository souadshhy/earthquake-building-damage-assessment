# AI handoff — Student 3: backend, geography and exports

## Whole-project context

We are a four-student team building a local earthquake building-damage inspection-support prototype. The system accepts supported before/after optical imagery, localizes buildings/groups in the pre-event image, creates paired crops, estimates damage with our trained classifier, converts pixel regions to geographic features, and shows an interactive map with suggested inspection tiers and CSV/GeoJSON downloads.

Regions/building groups are accepted targets. Do not assume one connected segmentation object is one verified physical building. Suggested high/medium/lower tiers support visual inspection planning, not structural-safety certification. Within-tier targets remain tied; model confidence is not a physical damage percentage or a justified within-tier urgency score.

Models are already selected:
- Frozen Microsoft pretrained UNet pre-event building branch: segmentation/localization only. Do not reuse its pretrained damage head as our trained damage classifier. A pinned checkpoint previously loaded and ran on one Mexico training image without weight updates. This is not held-out performance.
- Shared-encoder paired ResNet-18 initialized from ImageNet. It encodes both 224×224 crops with the same weights, concatenates before/after features and their absolute feature difference, and uses a new four-output head. ImageNet initialization originally recognized everyday objects, not damage. The new damage classifier requires supervised training.

Four native classes, in order: no-damage, minor-damage, major-damage, destroyed. Quantitative scoring retains all four; minor/major confusion remains wrong. The map alone groups probabilities as P(no damage), P(minor)+P(major), P(destroyed), then selects its display category. Preserve native probabilities/class in records.

## Frozen data decisions

| Role | Source | Prepared membership |
|---|---|---|
| Train | xBD Harvey + Michael + Mexico earthquake | 783 pairs, 77,338 eligible building annotations |
| Validation | xBD Florence | 319 pairs, 6,120 annotations |
| Primary test | xBD Matthew | 238 pairs, 13,155 annotations |
| External test | HaitiBRD 2010 earthquake | 139 reference regions: 83/32/16/8 |
| External test | EBD Türkiye 2023 earthquake | 1,461 reference regions: 1,433/19/3/6 |

External count order is no/minor/major/destroyed. Optional pooled result: 1,600 regions, support 1,516/51/19/14. Retain all four classes from both sources; no destroyed-only additions or oversampling. Separate source results are mandatory; pooling is supplementary. Neither external source enters training, validation, tuning or checkpoint selection. OCD-BDA is historical/inactive.

Source annotations have different provenance: manual satellite interpretation for Haiti, model-assisted/manual-corrected for EBD. Both document xBD-style criteria; do not claim identical annotation reliability or field-engineering truth. Haiti is one small original scene with twenty derived crops; those are not twenty independent scenes. Raw advertised building totals do not equal available classifier instances.

Data indexes: data/xbd_team_v1 and data/team_external_tests_v1. Data/weights/runs/runtime are local, ignored by Git. A fresh clone does not include pixels or checkpoints. Prepared Haiti input images are in data/haitibrd_prepared_v1, including twelve same-grid RGB GeoTIFF pairs. EBD has no established coordinates; never invent them. Reference GeoJSON contains labels and must not become a production inference input.

## Current implementation state

Data/source audits, split/config decisions, preparation scripts, classifier/evaluator code and detector sanity checking exist. The damage classifier has not been trained in this handoff and no damage accuracy has been measured. backend/app.py has health only; frontend/ is a buildable starter, not the interactive map. contracts/examples/result.fixture.json is explicitly synthetic developer data, not real predictions. Local source checks previously passed; inspect and rerun relevant checks after your changes instead of claiming old results verify new code.

The team goal is one real image pair → detected regions → genuine trained damage predictions → suggested tiers → interactive map → downloadable report. Classifier evaluation on reference crops is separate from complete detector/pipeline evaluation. Disclose possible detector pretraining overlap with xBD events.

## How to use this handoff

All paths below are relative to the repository root. Read the actual files before editing; do not rely only on this document. Read README.md, docs/handbook/STUDENT_PROJECT_GUIDE.md, docs/OWNERSHIP.md, docs/SETUP.md, docs/EXTERNAL_TESTS.md, docs/LABEL_CONTRACT.md, configs/dataset_roles.json and contracts/API.md as relevant.

This file provides project context and role boundaries. Follow the student's current request and newer agreed repository decisions; do not treat an older planning note as overriding an explicit current instruction. When this file is first provided, inspect the repository and establish the student's immediate task. Do not launch training, large downloads or unrelated implementation merely because they appear in the plan. Preparation so far ran no damage training. If the student explicitly requests the next authorized training stage, work within that stage and the hardware/data constraints.

Work on a branch, preserve teammates' changes and coordinate shared contracts/configuration/dependency edits. Own your module and matching report section; do not independently redesign the whole project. Keep interfaces backward compatible where feasible and update an example with any agreed change. Never fabricate model results, civil approval, geographic coordinates, tests or implemented endpoints.

Provide concise plain-language progress: what exists, what you changed, how checked, and the next handoff/blocker. If required data/weights are absent, identify the exact missing source/path and continue independent source work; do not pretend preparation or inference succeeded.

## Your role

Act as the technical assistant for Student 3. You own the local service that joins inputs, real model inference, geographic coordinates and downloadable reports. You coordinate backend/model integration. Do not train the damage model or redesign the frontend.

### Owned files

- backend/, especially backend/app.py, which currently has /health only.
- quake/geo.py and quake/io.py.
- Backend/geography/export tests under tests/.
- reports/backend/.

contracts/ is jointly owned with Students 2/4. Preserve Student 1's split/label records. pyproject.toml is shared.

## Work in this order

1. Read contracts/API.md and its fixture. Inspect actual backend routes; do not claim planned job/export routes already exist.
2. Agree input/result field names with Students 2/4. Publish matching request/response examples whenever the interface changes. Treat the existing example as synthetic; never serve it as real inference.
3. Implement input validation and a prepared-example path first. Accept aligned same-grid RGB GeoTIFF pairs up to 4096×4096, or validated prepared PNG examples with a geographic sidecar. Reject unsupported/missing geography and incompatible grids with clear messages.
4. Implement job creation, status and serial execution using SQLite metadata plus disk artifacts. Run one inference job at a time. Add readable failure states and empty-result handling.
5. Integrate Student 2's genuine inference function when a real checkpoint exists. Keep preprocessing/class order consistent. Do not replace it with constants or reference severity labels.
6. Convert predicted pixel polygons to WGS84 geographic shapes, retain IDs and create a point inside each polygon for tabular location/map links.
7. Implement CSV/GeoJSON exports and result retrieval. The API, map and both exports must agree on IDs/counts.
8. Connect one real prepared image pair with Students 2/4, then complete the upload workflow and edge cases.

## Required API direction

Planned routes in contracts/API.md:
- POST /jobs: validate inputs and create a job.
- GET /jobs/{job_id}: queued/running/completed/failed status.
- GET /jobs/{job_id}/buildings: result GeoJSON.
- GET /jobs/{job_id}/exports/csv and /exports/geojson: matching exports.

Define multipart field names/prepared-example request format explicitly before the upload UI is implemented. Routes above are requirements, not claims of existing implementation.

Pair inputs include image/pair IDs, dimensions, CRS, transform and provenance. Results include job/pair IDs, pixel/geographic geometry, four native probabilities/class, grouped display category/tier, model version and image IDs. Reference/predicted footprints and synthetic fixtures must remain distinguishable. Add crop URLs when the service actually serves them.

## Geographic facts that matter

Prepared Haiti demo_pairs.json indexes twelve 1024×1024 RGB GeoTIFF pairs. They were placed on the post-event grid; severity labels are absent from the input manifests. The full original Haiti image is 4400 pixels wide and exceeds the raw-upload cap. Use prepared tiles for the supported path.

Haiti reference GeoJSON is ground truth for evaluation/development, not detector output. Its severity properties must never leak into inference. EBD has no established geographic references; do not create map coordinates from invented assumptions.

xBD PNG geography is derived from original annotation correspondence and needs validation in the application. A fitted internal transform is not independent proof of absolute map accuracy. Preserve provenance and report conversion checks.

CRS describes the coordinate reference system. Affine transforms map image columns/rows into coordinates. GeoJSON uses longitude then latitude in WGS84. Test this order, image origin, axes and boundary behavior rather than trusting a visually plausible map. Use an interior representative point for CSV locations; a polygon centroid can fall outside some shapes.

Connected segmentation objects may contain several buildings. Preserve group identity; do not invent a one-to-one building inventory. Geometry repairs must not silently alter reference identity or drop result records.

## Priority and export rules

Keep four native probabilities. For display, sum minor+major before choosing among no apparent damage/damaged/destroyed. Current tiers are lower/medium/high respectively, with ties inside each tier. Model probability is not physical damage percentage or an engineering priority formula.

Counts in the map may be filtered, but the downloaded result scope must be clear. Agree filtered-versus-whole-job exports with Student 4 before implementing ambiguous behavior. Escape CSV fields correctly and preserve full probability/model provenance where required.

## Useful commands and checks

From the repository root:

    python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload

The frontend development /api proxy removes /api and targets this port. Local deployment is sufficient; do not add public hosting, radar input, arbitrary screenshot geolocation or PDF export.

Verify known pixel→coordinate examples, invalid CRS/grid inputs, empty predictions, inference failures, identical API/export IDs, serial job behavior and coordinate order. Tests should exercise meaningful boundary behavior; do not claim a health-only response proves the inference service works.

## Acceptance and report

Your first handoff is a documented, working API/record example that Student 4 can consume and Student 2 can populate. The real integration gate needs genuine model inference, validated geographic geometry and a matching downloadable row. The final backend handles supported inputs and errors without crashing.

Write reports/backend/ with validation, job/storage design, geographic method/checks, export behavior, integration and limitations. State exactly what is implemented versus scaffolded. Do not claim a completed application based on fixture output.
