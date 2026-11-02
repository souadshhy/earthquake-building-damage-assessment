# EBD Türkiye preparation and adoption — 2 November 2026

**Current handoff:** this is the EBD-only audit history. The active test suite now includes both HaitiBRD and EBD; use `EXTERNAL_TESTS.md`, `TEAM_PLAN.md` and the v3 ZIP. Earlier EBD-only assignments below are superseded by the two-source configuration.

## Decision

**Adopt EBD Türkiye in place of OCD-BDA as the supplementary external four-class test.** xBD partitions remain unchanged. EBD solves the three-versus-four category mismatch. It does not establish large-sample earthquake accuracy, geographic mapping support or perfect label reliability. No training or damage-model inference was performed.

Sources: Wang et al., [paper, DOI 10.34133/remotesensing.0733](https://doi.org/10.34133/remotesensing.0733); [Figshare release v2](https://doi.org/10.6084/m9.figshare.25285009.v2). Downloaded only `EARTHQUAKE-TURKEY.zip`, file ID 44696047. Metadata and provenance are retained in `technical_checks/test_dataset_search/ebd_figshare.json` and `data/ebd_turkey/source.json`.

## Completed checks

- Full archive: 931,980,914 bytes; published MD5 `f4c99f2b91f6978e5fa8edf3d5a60171` verified.
- All 3,776 PNG files CRC-checked, fully decoded and SHA-256 indexed.
- Exactly 944 matched before/after pairs with both corresponding masks. Images are 512×512 RGB; masks are single-channel.
- All pre-event values are 0/255. Post-event values are 0/background and 1/2/3/4 for no/minor/major/destroyed. Every category is present.
- Post-event pixel counts: background 221,992,049; no damage 24,424,608; minor 424,157; major 376,078; destroyed 247,044. Pixels are not independent buildings.
- No exact-image repeats within EBD, and no exact-file matches with the prepared xBD partitions. Hash checks do not rule out every near-duplicate or shared source scene. Distinct event roles and dataset provenance remain part of the separation rationale; source-footprint geographic nonoverlap cannot be certified without coordinates.
- Automatic pair checks: 197 consistent with a common grid, 137 offset flags, 610 inconclusive. These are feature-registration diagnostics, not certified per-building correspondence. No image warping was applied.

## Frozen reference regions

Use 8-connected components of the pre-event building mask. Reject regions smaller than 16 pixels, touching an image boundary, containing multiple/nonexistent nonzero damage classes, or having less than 95% severity-mask coverage. Never turn a mixed region into a label by majority vote.

16,937 components were found: 11,044 retained and 5,893 excluded. Exclusion reasons overlap: 5,104 border-truncated; 886 very small; 291 mixed/missing severity. Touching same-class buildings may still be merged, so these are **reference regions, not verified individual buildings**.

For paired scoring, also require at least 12 registration inliers, spatial coverage >=0.05, scale 0.9–1.1, median displacement <=8 pixels, and fitted displacement at the region center <=20% of its shorter box side. Exact duplicate pairs would be removed. These preparation rules do not depend on model scores.

| Native class | Clean reference regions | Regions passing paired screen |
|---|---:|---:|
| No damage | 10,913 | 1,433 |
| Minor | 60 | 19 |
| Major | 23 | 3 |
| Destroyed | 48 | 6 |
| Total | 11,044 | 1,461 |

9,583 otherwise clean regions do not pass the additional paired screen. Retain them and their pair diagnostics for traceability; do not equate an inconclusive screen with proven unusability. `paired_verified_regions.jsonl` is the active, conservative external classifier subset. This selection may favor easier imagery; report this scope and selection bias. With only 3 major and 6 destroyed examples, do not claim robust performance on those classes. The full 944-pair release must not be represented as 944 validated paired-classifier scenes.

The example sheet is a source-label illustration, not independent confirmation of the labels or a model output. Some are drawn from the broader reference set. Mask-derived regions and apparent visual severity can disagree; original labels were not rewritten to fit visual expectations.

## What each file means

All files below are in `data/team_ebd_external_v1/`:

- `manifest.json`: counts, class order, rules, source, limitations and SHA-256 hashes of frozen tables.
- `pairs.json`: paths to both images and masks, dimensions, pair IDs and registration diagnostics.
- `reference_regions.jsonl`: clean mask-derived regions from the complete release.
- `paired_verified_regions.jsonl`: frozen records used by the four-class paired evaluator.
- `region_exclusions.json`: excluded component IDs and reasons.
- `source_files.json`: all decoded source paths, archive members, CRCs and SHA-256 values.
- `exact_duplicate_groups.json`: exact repeated-image groups (none found).

A manifest is an index/record of dataset membership and provenance. The `.jsonl` tables contain one JSON record per line, rather than the image pixels. Paths currently refer to this preparation laptop.

## Geography and annotation provenance

No geographic sidecars or established raster georeference are supplied in this archive. Keep xBD as the initial geographic demonstration source; do not invent EBD coordinates. Geographic conversion and validation still belong to Student 3.

The four categories follow xBD criteria according to EBD's authors, but reference labels are model-assisted and manually corrected. They are not independent field-inspection truth. We use our own separately trained classifier, not EBD target-trained weights. The metadata license is CC BY 4.0; preserve citation and underlying imagery terms when transferring data.

## Another-laptop setup (preparation only)

Create a Python environment and install the project from `pyproject.toml`. Transfer the xBD original archive. Transfer `data/ebd_turkey/EARTHQUAKE-TURKEY.zip` or download it using:

```powershell
python scripts/fetch_ebd_turkey.py
```

The downloader verifies the complete MD5 and recreates source provenance even for an already transferred archive. The handoff ZIP contains machine-local manifests for reference. **Move its two generated folders `data/xbd_team_v1` and `data/team_ebd_external_v1` outside the checkout before regenerating on another machine.** Keep them as records; do not merely edit frozen rows in place. Then run:

```powershell
python scripts/prepare_team_datasets.py --external ebd --archive 'D:\datasets\train_images_labels_targets.tar'
```

This extracts/checks data and rebuilds absolute paths. It does not train. Keep regenerated manifests, checksum status and exclusions together. Repeated preparation on the original laptop checks existing frozen-table hashes instead of replacing tables.

## Later evaluation, after training

Student 2 trains and freezes the model using xBD training/validation only. Student 1 then runs:

```powershell
python -m quake.cli evaluate-ebd --data data/team_ebd_external_v1 --checkpoint runs/paired_v1/best.pt --output runs/paired_v1/ebd_test.json
```

This command is implemented but has not been run: there is no trained damage checkpoint. It retains all four classes and reports per-class support, precision, recall, F1, macro-F1 and a confusion matrix. No probability grouping is used for scoring. Classification on reference regions is separate from detection/full-pipeline evaluation. Do not score inferred merged objects as verified individual buildings.
