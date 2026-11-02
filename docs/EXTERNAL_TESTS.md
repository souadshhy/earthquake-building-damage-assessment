# External tests: HaitiBRD + EBD

## Current decision

Use both frozen audited subsets, with four native categories. Keep the complete eligible subset from each source, rather than adding destroyed examples alone. Neither source enters training, validation, tuning or checkpoint selection.

| Source | No damage | Minor | Major | Destroyed | Total |
|---|---:|---:|---:|---:|---:|
| HaitiBRD | 83 | 32 | 16 | 8 | 139 |
| EBD Türkiye | 1,433 | 19 | 3 | 6 | 1,461 |
| Optional combined test | 1,516 | 51 | 19 | 14 | 1,600 |

These are reference regions/building groups, not guaranteed individual buildings. Report each source separately. An optional combined result pools reference records; the larger EBD set dominates it. It does not establish performance across 1,600 independent scenes. The sources cover two events, with Haiti originating from one small scene. Fourteen destroyed regions still give limited severe-class evidence. The xBD Matthew test remains the primary quantitative test.

## Files the team should use

`data/team_external_tests_v1/`:

- `manifest.json`: class order, counts by source, provenance, duplicate checks and frozen table hashes.
- `regions.jsonl`: all 1,600 test records, each with source, source group, unique ID, paths, bounding box and four-class label.
- `haitibrd_regions.jsonl` and `ebd_regions.jsonl`: the same membership separated by source.
- `haitibrd_reference_regions.geojson`: 139 reference geometries; explicitly not predictions. Do not feed severity fields into inference.
- `exclusions.json`: links to source exclusions; Haiti cropped areas 16–20 remain excluded because of conflicting masks.
- `prepared_image_sha256.json`: hashes for the prepared Haiti input images.

`data/haitibrd_prepared_v1/`:

- `before_rgb_post_grid.png`, `after_rgb.png`: RGB originals used by the reference-crop classifier loader. Before imagery was resampled to the post-event geographic grid using bilinear interpolation. Damage labels and selected IDs were not changed.
- `pair.json`: input geography, dimensions, provenance and hashes.
- `demo_pairs.json` plus 24 RGB GeoTIFFs: 12 same-grid 1024×1024 before/after pairs within the supported application size. These inputs contain no severity labels. They are future demo inputs, not completed model predictions.

Existing EBD original masks, raw images and frozen audit records stay in `data/ebd_turkey` and `data/team_ebd_external_v1`. EBD coordinates remain unavailable; do not invent them. Existing Haiti source images remain in `technical_checks/test_dataset_search/haitibrd/files`. The full original Haiti image is 4400 pixels wide and is not a supported direct application upload; use prepared tiles.

A manifest is a dataset index. JSONL files have one record per line. Images are stored separately; sending the index alone does not send the images.

## Label and duplicate handling

Both releases document xBD-compatible no/minor/major/destroyed criteria. Four-class scoring preserves minor-to-major errors. The map may use its separate three-category grouping. Haiti annotations are manual satellite-image interpretations; EBD annotations are model-assisted/manual-corrected. Report the provenance difference. These are not field-engineering safety labels.

Haiti's palette PNG storage indices are not severity numbers. The audited conversion is index 0→background, 1→major, 2→no damage, 3→minor, 4→destroyed; RGB colors carry the equivalent meanings. Retain the original source masks. The suite uses already-audited semantic labels, never raw palette positions as class indices.

Haiti reference regions are extracted once from the original scene. Cropped copies are demonstration assets, not extra test examples. IDs are namespaced by dataset. Cross-source exact-file hashes have no matches; the audit found no Haiti overlap with the prepared xBD geographic extents. EBD internal exact duplicates were absent. Exact hashes cannot rule out every near-duplicate; EBD lacks coordinates for a complete geometric overlap check. Do not claim globally certified independence.

## Commands and transfer

Recheck/build on this preparation laptop:

```powershell
python scripts/prepare_team_datasets.py --external suite
```

The preparation command builds the current HaitiBRD/EBD suite. Frozen outputs are checked before reuse.

On another laptop, install this project and transfer the original xBD archive, EBD archive/provenance and Haiti source files under their release terms. Git contains code and small source audit metadata; raw images, prepared image pixels and weights transfer separately. Transfer `technical_checks/test_dataset_search/haitibrd/files` as a folder; alternatively use the included public downloader `python scripts/inspect_haitibrd.py --stage download`. EBD download: `python scripts/fetch_ebd_turkey.py`.

Current manifests contain preparation-laptop absolute paths. Before regenerating elsewhere, move the copied generated folders `data/xbd_team_v1`, `data/team_ebd_external_v1`, `data/team_external_tests_v1`, and `data/haitibrd_prepared_v1` outside the checkout as records. Keep the source archives/raw data and supplied Haiti audit records. Run `python scripts/prepare_team_datasets.py --external suite --archive 'D:\datasets\train_images_labels_targets.tar'`. This regenerates paths and hashes; never silently hand-edit frozen membership. Confirm the source-specific counts match the frozen counts above and investigate differences before evaluating.

Later, after a real damage model has been trained and frozen using xBD only:

```powershell
python -m quake.cli evaluate-external --data data/team_external_tests_v1 --checkpoint runs/paired_v1/best.pt --output runs/paired_v1/external.json --include-combined
```

Per-source metrics are always produced; omit `--include-combined` to skip pooling. The evaluator preserves source IDs, four-class support/confusion matrices and checkpoint provenance. No training or damage evaluation has been run during preparation. Reference-crop scores are not automatic detection/full-pipeline scores.

Sources: [HaitiBRD v2](https://doi.org/10.17603/ds2-fqat-4v02), [EBD v2](https://doi.org/10.6084/m9.figshare.25285009.v2). Preserve citation, release licenses and underlying imagery terms.
