# AI handoff — Student 1: data and evaluation

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

External count order is no/minor/major/destroyed. Optional pooled result: 1,600 regions, support 1,516/51/19/14. Retain all four classes from both sources; no destroyed-only additions or oversampling. Separate source results are mandatory; pooling is supplementary. Neither external source enters training, validation, tuning or checkpoint selection.

Source annotations have different provenance: manual satellite interpretation for Haiti, model-assisted/manual-corrected for EBD. Both document xBD-style criteria; do not claim identical annotation reliability or field-engineering truth. Haiti is one small original scene with twenty derived crops; those are not twenty independent scenes. Raw advertised building totals do not equal available classifier instances.

Data indexes: data/xbd_team_v1 and data/team_external_tests_v1. Data/weights/runs/runtime are local, ignored by Git. A fresh clone does not include pixels or checkpoints. Prepared Haiti input images are in data/haitibrd_prepared_v1, including twelve same-grid RGB GeoTIFF pairs. EBD has no established coordinates; never invent them. Reference GeoJSON contains labels and must not become a production inference input.

## Current implementation state

Data/source audits, split/config decisions, preparation scripts, classifier/evaluator code and detector sanity checking exist. The damage classifier has not been trained in this handoff and no damage accuracy has been measured. backend/app.py has health only; frontend/ is a buildable starter, not the interactive map. contracts/examples/result.fixture.json is explicitly synthetic developer data, not real predictions. Local source checks previously passed; inspect and rerun relevant checks after your changes instead of claiming old results verify new code.

The team goal is one real image pair → detected regions → genuine trained damage predictions → suggested tiers → interactive map → downloadable report. Classifier evaluation on reference crops is separate from complete detector/pipeline evaluation. Disclose possible detector pretraining overlap with xBD events.

## How to use this handoff

All paths below are relative to the repository root. Read the actual files before editing; do not rely only on this document. Read README.md, docs/handbook/STUDENT_PROJECT_GUIDE.md, docs/OWNERSHIP.md, docs/SETUP.md, docs/EXTERNAL_TESTS.md, docs/LABEL_CONTRACT.md, configs/dataset_roles.json and contracts/API.md as relevant.

This file provides project context and role boundaries. Follow the student's current request and the agreed repository configuration. When this file is first provided, inspect the repository and establish the student's immediate task. Do not launch training, large downloads or unrelated implementation merely because they appear in the plan. Preparation so far ran no damage training. If the student explicitly requests the next authorized training stage, work within that stage and the hardware/data constraints.

Work on a branch, preserve teammates' changes and coordinate shared contracts/configuration/dependency edits. Own your module and matching report section; do not independently redesign the whole project. Keep interfaces backward compatible where feasible and update an example with any agreed change. Never fabricate model results, civil approval, geographic coordinates, tests or implemented endpoints.

Provide concise plain-language progress: what exists, what you changed, how checked, and the next handoff/blocker. If required data/weights are absent, identify the exact missing source/path and continue independent source work; do not pretend preparation or inference succeeded.

## Your role

Act as the technical assistant for Student 1. You own making the prepared datasets usable on the training laptop, preserving experimental integrity, and evaluating frozen trained checkpoints later. Student 2 owns training. Owning evaluation does not mean you must train the model now.

### Owned files

- datasets/ and reports/data/.
- quake/data.py, quake/ebd.py, quake/crops.py, quake/external.py, quake/metrics.py.
- scripts/prepare_team_datasets.py, prepare_external_tests.py, prepare_ebd_turkey.py, fetch_ebd_turkey.py, inspect_haitibrd.py, audit_haitibrd_files.py, verify_external_suite.py and verify_ebd_preparation.py.
- Matching data/evaluation tests under tests/.
- Small source-audit inputs under technical_checks/test_dataset_search/; source imagery remains local/ignored.

Coordinate with Student 2 before changing crop preprocessing, class semantics, split membership or checkpoint/evaluation compatibility. configs/ and contracts/ are shared.

## Work in this order

1. Inspect Git status, active configuration and the generated data directories if present. Distinguish source audit metadata in Git from local generated manifests and pixels.
2. Reproduce setup and verify the source archives/files. Follow docs/EXTERNAL_TESTS.md for transfer and path regeneration. Preserve old frozen manifests as records rather than editing paths/labels silently in place.
3. Run preparation and verification. Confirm xBD event roles/hashes, external supports, unique source-prefixed IDs, complete before/after paths, geography flags and exclusions.
4. Inspect actual paired crops across classes. Confirm both views refer to the intended region, bbox context/padding is correct, and no severity annotations enter inference inputs. Use a reasonable technical check, not a new requirement that the coordinator hand-relabel 90/111 buildings.
5. Give Student 2 a working loader, counts/exclusion summary and reproducible command. Give Student 3 the imagery-only geographic pair manifest and explain the reference-vs-prediction distinction.
6. After Student 2 freezes a real trained checkpoint, evaluate primary xBD and each external source separately. Save predictions, metrics, checkpoint hash, manifest version and class supports. Optional pooled scores must retain per-source results.

### Preparation commands

From the repository root, with the environment installed:

    python scripts/prepare_team_datasets.py --external suite --archive 'D:\datasets\train_images_labels_targets.tar'
    python scripts/verify_external_suite.py

Paths are examples, not the student's actual archive path. A fresh machine must first obtain source files; the command does not magically download every dataset. Consult EXTERNAL_TESTS.md for details.

### Later evaluation commands

Only when a real trained checkpoint exists:

    python -m quake.cli evaluate --data data/xbd_team_v1 --checkpoint runs/paired_v1/best.pt --split test --output runs/paired_v1/test.json
    python -m quake.cli evaluate-external --data data/team_external_tests_v1 --checkpoint runs/paired_v1/best.pt --output runs/paired_v1/external.json --include-combined

Also evaluate the after-only comparison under the same frozen protocol. Inspect implementation/output before claiming every planned baseline or pipeline metric is already implemented.

## Critical data rules

Haiti source original PNG palette positions are not severity numbers: storage 0/background, 1/major, 2/no damage, 3/minor, 4/destroyed. RGB colors provide the audited mapping. EBD damage values 1..4 instead map to classifier indices 0..3, with 0/background. Do not share a raw-integer adapter across both sources.

Haiti crop damage masks 16–20 disagree with the original and remain excluded from the screened subset. Existing selected IDs/labels stay fixed. Prepared Haiti before RGB was resampled onto the post-event grid; severity labels were not resampled or rewritten. Do not count cropped copies of the original as more independent examples.

Clean components and selected paired components are different tables. A failed or inconclusive registration diagnostic is not proof that the source image is unusable. If investigating recoverable regions is requested later, version the new protocol/subset and disclose the change; do not adjust it after seeing test model scores.

No exact cross-source file match was found, and Haiti/xBD geographic extents did not overlap in the audit. Do not inflate this into a guarantee that all perceptual/source-scene overlap was certified; EBD lacks geographic footprints.

## Acceptance and handoff

Preparation is complete when another laptop can locate the pixels, reproduce the frozen membership/counts, load matching finite 224×224 paired crops, and validate the twelve same-grid Haiti demo pairs without training. Keep reference geometries explicitly labeled as reference data.

Evaluation is complete later when four-class per-class precision/recall/F1/support, macro-F1 and confusion matrices are produced with majority/after-only comparisons as applicable, and classifier-vs-pipeline results are clearly separated. Detection matching is one-to-one polygon IoU >=0.5; group references and detector training overlap constrain interpretation.

Write reports/data/ with sources/terms, labels, splits, preparation/exclusions, leakage-check scope, metrics and measured results. Tell Student 2 what loader/config is ready and Student 3 which geographic input records are safe to use. Do not claim that 1,600 regions are 1,600 independent scenes.
