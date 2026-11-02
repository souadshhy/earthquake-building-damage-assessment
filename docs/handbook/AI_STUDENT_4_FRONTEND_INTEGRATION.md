# AI handoff — Student 4: frontend and integration

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

Act as the technical assistant for Student 4. You own the browser interface and coordinate the integrated demonstration. The interactive map is the main user output, not an optional illustration. Do not take over data preparation, model training or backend implementation.

### Owned files

- frontend/, including src/App.tsx, main.tsx, style.css, vite.config.ts, tsconfig.json, package.json and package-lock.json.
- Frontend tests and reports/frontend/.

Coordinate contracts/ with Student 3 and model-facing probability semantics with Student 2. Do not change configs/dataset_roles.json, source labels or held-out membership.

## Work in this order

1. Read the actual frontend starter and contracts/API.md. The current page shows no assessment loaded; it is not a map implementation.
2. Agree API response/request shapes with Student 3, including job status, crop URLs, result geometry and export scope.
3. Build the interactive map and linked building/group list using contracts/examples/result.fixture.json. Mark fixture/development mode visibly and never call it a real model output.
4. Add category and tier filters, summary counts, click details and before/after crop display when URLs/images are available.
5. Implement prepared-example selection first, then paired GeoTIFF upload against the actual agreed endpoint. Include loading, queued/running, completed, failed and empty states.
6. Replace fixture mode with the real job API when Student 3's routes exist. Poll status responsibly and display genuine outputs.
7. Add CSV/GeoJSON downloads from backend exports, preserving the agreed whole-job/filtered scope.
8. Coordinate an early end-to-end demonstration with Students 2/3 and document setup for a second laptop.

## Technical starting point

Use the existing React/TypeScript + Leaflet stack; do not independently replace frameworks or add public hosting. Install from the committed package-lock.json and commit lockfile changes with intentional dependency changes.

From frontend/:

    npm ci
    npm run dev
    npm run build

The Vite /api proxy targets http://127.0.0.1:8000 and strips the /api prefix. Student 3 starts the backend separately. Only /health currently exists; planned job/export routes are not implemented simply because they appear in the contract.

## What the interface must do

- Show geographic predicted regions with damage-category colors and a clear legend.
- Let the user click a region or list entry to see the matching ID, building/group type, damage estimate, model probabilities and before/after crops.
- Provide category/tier filters and counts that match the visible result scope.
- Show a linked list ordered by suggested tier: high, medium, lower. Within-tier objects tie; do not manufacture structural urgency from confidence.
- Download actual matching CSV/GeoJSON reports from the backend.
- Clearly distinguish predicted footprints, reference footprints and synthetic developer fixtures.
- Handle unsupported inputs, failed jobs, no detections and missing crop images without presenting fake success.

Use geography returned by the backend; do not guess coordinates or independently reconstruct them from image names. Prepared Haiti examples can support maps, whereas EBD has no established map coordinates. Never substitute arbitrary pins for geolocated predictions.

## Probability and priority meaning

The model's native order is no damage, minor, major, destroyed. Retain/display native information in details as appropriate. The overview groups minor+major by summing their probabilities before selecting a three-category display winner. The resulting categories map to lower/medium/high suggested inspection tiers.

A probability of 70% damaged means model probability assigned to the minor-or-major group, not 70% physical building damage. A confident minor prediction is not automatically more urgent than a less confident major prediction. Lower priority does not certify safety. Destroyed is an image label, not automatically independently confirmed collapse.

It is acceptable for the native winning class and the grouped winning display category to differ; follow the shared conversion rather than hard-renaming the native argmax. Four-class evaluation belongs to Student 1; do not display grouped accuracy as though it were four-class performance.

## Integration and verification

Use stable region IDs to link map, list, details and reports. Preserve GeoJSON longitude/latitude order; Leaflet utilities may use latitude/longitude arrays, so convert explicitly when needed. Do not copy fixture coordinates into real results.

Agree whether downloads represent the whole job or current filters, and label the behavior. Check filter changes, empty groups, count consistency, click/list linking, job failures and download IDs. A successful npm build checks compilation, not map correctness; inspect the actual interface and exercise meaningful interactions once implemented.

The first week should produce a small genuinely connected example, not four polished isolated modules. Before a trained checkpoint exists, clearly labeled fixture integration is useful development but does not satisfy the real prediction milestone.

## Acceptance and report

Your first handoff is a usable map/list/filter flow against a marked fixture and an agreed API. The real gate is one actual image pair processed by Student 2's trained classifier through Student 3's backend, visible with valid geography and matching exports.

Write reports/frontend/ with the user workflow, map/list behavior, category/tier explanation, API integration, error handling, checks, demo and limitations. Coordinate another-laptop setup and rehearsal. Never report synthetic fixture screenshots as model experiments.
