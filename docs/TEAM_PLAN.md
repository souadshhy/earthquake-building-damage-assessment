# Team plan — earthquake damage and inspection map


## Current implementation

Dataset preparation and model selection are complete. The detector passed a one-image inference check without weight updates. The damage classifier is written but untrained. The backend has a health endpoint and the frontend has starter code; real inference jobs and the interactive map remain to be built. Confirm training-laptop GPU/VRAM/RAM/OS before training.

## Product

Build a local interactive map of predicted buildings/building groups, damage and suggested visual-inspection tiers. Support prepared examples and aligned, same-grid RGB GeoTIFF pairs up to 4096×4096. Validate geography; reject incompatible grids. xBD PNG examples require a validated geographic sidecar. Source severity labels must never enter inference inputs.

The map has colored geometries, click details, before/after crops, category/tier filters, linked building list, counts and CSV/GeoJSON downloads. Priority tiers are high/medium/lower; within-tier buildings tie. This supports inspection planning, not structural-safety certification or operational dispatch. Model probability is not physical damage percentage. No invented repair/priority formula is required.

## Frozen dataset roles

| Role | Dataset/events | Image pairs | Eligible annotations/regions |
|---|---|---:|---:|
| Train | xBD Harvey + Michael + Mexico earthquake | 783 | 77,338 building annotations |
| Validation | xBD Florence | 319 | 6,120 building annotations |
| Primary test | xBD Matthew | 238 | 13,155 building annotations |
| External Haiti test | HaitiBRD | One original scene / 20 derived crops | 139 screened reference regions |
| External Türkiye test | EBD | 944 source pairs | 1,461 screened reference regions |

HaitiBRD and EBD are separate held-out external tests. The optional combined result contains 1,600 reference regions, including 14 destroyed. Keep all four classes and original source IDs; report each dataset separately. Türkiye and Haiti never enter training/tuning. Three-category grouping is only the map display. See `EXTERNAL_TESTS.md` for membership, geographic inputs, exclusions and transfer instructions.

These selected reference regions may contain multiple buildings. Sparse severe examples, annotation provenance and quality-screen selection remain report limitations. xBD Matthew remains primary.

## Selected models

- Building localization: frozen, pinned Microsoft UNet pre-event branch. Restricted loading, adapter equivalence and inference on one Mexico training image passed. Retain source/license and checkpoint provenance; disclose possible detector pretraining overlap with xBD tests. Its pretrained damage head is not our classifier.
- Damage classification: shared ImageNet-initialized ResNet-18 encoder for before/after crops; concatenate both feature vectors and their absolute difference; new four-class head. Supervised paired-image classification, trained later on xBD labels.
- Crops: same bounding window in both images, 20% context on each side, edge padding, resize 224×224, ImageNet normalization, identical flips/rotations.
- Starting training settings: head-only 3 epochs, fine-tune up to 20 more; AdamW head 1e-3/encoder 1e-4, weight decay 1e-4; seed 42; train-only inverse-square-root class weights normalized to mean one; validation macro-F1 selection, patience 5; batch 16 adjusted to measured memory. Do not alter held-out class distributions.

## Four students: files and first deliverables

| Student | Owns | Start in these files/folders | First deliverable |
|---|---|---|---|
| 1 — Data/evaluation | Data transfer, crop checks, frozen splits, metrics | `docs/EXTERNAL_TESTS.md`, `docs/LABEL_CONTRACT.md`, `scripts/prepare_team_datasets.py`, `quake/data.py`, `quake/ebd.py`, `quake/crops.py`, `quake/metrics.py`, `quake/external.py`, `scripts/prepare_external_tests.py`; `data/xbd_team_v1`, `data/team_external_tests_v1` | Reproduce counts and paths on training laptop; check matching before/after crops; preserve exclusions and hashes. Later evaluate Student 2's frozen model and produce tables. |
| 2 — Models/training | Detector, paired classifier, after-only baseline, inference | `quake/detector.py`, `quake/models.py`, `quake/training.py`, `quake/cli.py`, `scripts/download_weights.py`, `scripts/verify_detector.py` | Confirm hardware; reproduce detector-only check. Later tiny training-only learning check, then trained reloadable checkpoints and inference function. |
| 3 — Backend/geography/reports | Pair validation, jobs, API, coordinates, exports | `quake/geo.py`, `quake/io.py`; create backend/API module and tests | Document request/result example; validate xBD sidecar and prepared Haiti GeoTIFF geography; return one prediction record with geometry and matching CSV/GeoJSON. |
| 4 — Frontend/integration | Interactive map, linked list, filters, status, downloads | `frontend/` (implementation remains to be built), shared API fixture from Student 3 | Build interactive map against fixture, then real API; demonstrate click/filter/count/download consistency and errors. |

Student 3 coordinates model/backend interfaces; Student 4 coordinates integration/demo. Students 1 and 2 jointly approve and record experimental changes. Every student writes their report section. Assign actual names during the meeting.

Data preparation and evaluation are one ownership role across the project: Student 1 prepares now, then evaluates later; Student 2 owns training. The existing manifests are indexes, not the final crop-validation work or model results.

## Shared interfaces and implementation

Use Python/PyTorch + FastAPI, React/TypeScript + Leaflet, SQLite job metadata and artifacts on disk. One inference job at a time.

Pipeline: validate pair → localize pre-event buildings → paired crops → classify → geographic conversion → map/export.

Pair record: image paths/IDs, dimensions, transform/CRS, provenance. Result record: building ID, pixel and geographic geometry, four probabilities/native class, three display probabilities/category, suggested tier, model version and image IDs. Distinguish predicted footprints from reference footprints. CSV uses an interior polygon point and map link. API: create job, poll status, retrieve GeoJSON, download CSV/GeoJSON. Include a matching example whenever an interface changes.

xBD sidecars and 12 prepared Haiti geographic image pairs support map integration. Student 3 validates their conversion and uses imagery-only input manifests. EBD has no established geography; do not invent its map locations.

## Milestones after preparation

| Period | Acceptance gate |
|---|---|
| Days 1–3 | Transfer/reproduce data; confirm hardware; detector inference; later training-only tiny learning check; one real prediction, geographic feature and report row |
| Days 4–7 | One actual prediction visible on interactive map; API/model integration; paired-crop and geography checks |
| Week 2 | Main paired training and after-only comparison on identical xBD partitions; prepared examples/uploads, filters and exports |
| Week 3 | Freeze model/settings; native four-class xBD test; separate HaitiBRD/EBD four-class region tests; optional combined result; localization/full-pipeline error analysis |
| Week 4 | Report, reproducibility package, another-laptop setup, demonstration rehearsal; reserve final 3 days for fixes |

Daily 15-minute check-in; integrate at least twice weekly. Do not wait for four finished isolated modules.

## Evaluation and completion

Report classifier four-class precision/recall/F1/support, macro-F1 and confusion matrices, training-majority baseline and after-only comparison. External evaluation uses `data/team_external_tests_v1/regions.jsonl`; report HaitiBRD/EBD separately and disclose selected-region scope and severe-class support. Do not use grouped map outputs as the four-class scores.

Evaluate automatic detection separately using one-to-one polygon IoU>=0.5, reporting misses, false detections and merged regions. Classification on reference locations is not full-pipeline accuracy. Disclose detector-training overlap; affected xBD pipeline demonstrations are descriptive, not clean unseen-event evidence. EBD semantic reference regions do not supply verified individual-building matching truth.

Completion requires reloadable trained damage weights; reproducible partitions/results; real supported-pair inference and valid geographic exports; matching map/report counts; invalid/empty/error handling; successful second-laptop setup; report with sources, terms, limitations and reproducibility. No accuracy target is promised before a baseline. No public hosting, radar, after-only upload workflow, arbitrary screenshot geolocation, address guarantee or PDF export is required.

## Preparation and later commands

See `EXTERNAL_TESTS.md` for download, transfer and path regeneration. Do not reuse preparation-laptop absolute paths on another machine. Git excludes raw images, weights and generated run outputs.

After hardware/data checks, when beginning the training stage:

```powershell
python -m quake.cli train --data data/xbd_team_v1 --output runs/tiny_paired --tiny
python -m quake.cli train --data data/xbd_team_v1 --output runs/paired_v1
python -m quake.cli train --data data/xbd_team_v1 --output runs/after_only_v1 --mode after_only
python -m quake.cli evaluate --data data/xbd_team_v1 --checkpoint runs/paired_v1/best.pt --split test --output runs/paired_v1/test.json
python -m quake.cli evaluate-external --data data/team_external_tests_v1 --checkpoint runs/paired_v1/best.pt --output runs/paired_v1/external.json --include-combined
```
