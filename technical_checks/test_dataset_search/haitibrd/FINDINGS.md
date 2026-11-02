# HaitiBRD versus EBD: completed candidate audit

**Subsequent authorized preparation is complete:** HaitiBRD and EBD now form separate held-out tests in `data/team_external_tests_v1`, with optional combined reporting. Use `docs/EXTERNAL_TESTS.md` and the v3 handoff. Statements below that integration was pending describe the audit-stage status; the source findings and counts remain applicable.

## Decision

**HaitiBRD v2 is the better candidate for the project's region-level external earthquake test and geographic demonstration. It does not solve all limitations, and it is not yet an integrated replacement in the active configuration.** Its advantages are an explicitly documented xBD damage scale, manual source annotation and actual raster georeferencing. Severe-class support remains limited after conservative filtering. Keep the large xBD held-out test as the primary quantitative evaluation.

The user's accepted targets include building groups/regions. That makes semantic-region references acceptable if outputs and evaluation state that scope. Neither dataset supports claiming every connected region is a separate building.

No damage-model inference, optimization or training was run. No user relabeling requirement is introduced.

## Evidence inspected

- [Original release and citation](https://doi.org/10.17603/ds2-fqat-4v02), PRJ-4169, version 2.
- Authors' `HaitiBRD_readme.pdf` (v2 report dated June 2026): all four pages extracted; the classification table on page 2 was also rendered and visually checked. Saved in `files/` and `readme_text.txt`.
- Public publication metadata and file inventory: `../haitibrd_publication.json`, `inventory.json` and saved directory responses.
- Downloaded and decoded 42 image TIFFs (one original pair plus twenty cropped pairs), 42 building-mask PNGs, the PDF report and the label illustration: 86 files, checked against repository byte lengths and indexed by SHA-256 in `source_sha256.json`.
- Full-raster data and masks processed by `scripts/audit_haitibrd_files.py`; exact results in `audit.json`, per-pair details in `pair_audit.json`.

Road files are outside this building-damage audit. The road directory listing was limited to its first 100 entries; this does not affect the complete image/building-mask inventory.

## Comparison

| Requirement | EBD Türkiye audit | HaitiBRD v2 audit | Finding |
|---|---|---|---|
| Four xBD-style categories | Authors describe xBD criteria | Data report explicitly describes the xBD Joint Damage Scale and defines all four levels | Category correspondence documented for both |
| Reference-label provenance | Model-assisted with manual correction | Report describes manual satellite-image interpretation and contributor review | HaitiBRD avoids the documented EBD teacher-generated-label dependence; neither is field inspection truth |
| Before/after optical imagery | 944 source pairs | One original scene pair, supplied as 20 derived crops | Both fit the image modality; crops are not independent events |
| Geographic metadata | No established georeference in supplied PNG archive | All 42 TIFFs carry EPSG:4326 and geographic affine transforms | HaitiBRD solves the missing-raster-coordinate problem at metadata level |
| Registration diagnostic | 197/944 pairs consistent; others flagged/inconclusive | 19/20 cropped pairs consistent; 1 inconclusive | Stronger technical pairing evidence, not certified per-building alignment |
| Conservative paired class supports | 1,433 / 19 / 3 / 6 | 83 / 32 / 16 / 8 | More minor/major and slightly more destroyed support; much smaller total reference subset |
| Independent scene breadth | Many tiles from one event | One small source scene, about 3.51 km² | HaitiBRD is geographically narrow; do not claim broad earthquake generalization |

Supports are **no damage / minor / major / destroyed reference regions**, not verified individual buildings. Our common feature diagnostic uses 512×512 views; HaitiBRD's 1024×1024 crops were reduced for that diagnostic and fitted displacements were converted back to original pixels for region screening. These are preparation diagnostics, not model scores or a validation of the thresholds.

## What the file audit found

Original imagery is 4400×3200 with red, green, blue and alpha bands. Its location is approximately longitude -72.3493 to -72.3290 and latitude 18.5410 to 18.5558. No footprint overlap or exact-file matches were detected against the prepared xBD partitions.

Before/after affine origins differ by approximately 0.219 pixels horizontally and 0.103 vertically. This is small but not an identical grid. Prepared inputs still need RGB-band selection and deliberate common-grid handling. The original width also exceeds the application's 4096-pixel cap; use prepared tiles rather than promising direct full-scene upload.

**Encoding trap:** the original post-event PNG is palette-indexed. Raw palette index 1 is major, 2 is no damage, 3 is minor, 4 is destroyed; 0 is background. These storage indices must be decoded by their colors. They must not be treated as the report's numbered severity codes. The adapter in the audit handles both palette and RGB masks. The original pre-event mask is binary.

**Crop inconsistency:** all cropped RGB content and pre-event footprint masks agree with their corresponding original windows. However, the five cropped post-event damage masks numbered 16–20 disagree with the original damage mask in the bottom strip. Differences are 90,597; 64,462; 54,154; 53,836; 77,391 pixels respectively. These crop areas are excluded from the conservative comparison subset; no conflicting label is silently rewritten. This does not mean the other 15 crops are independently field-validated.

The release reports more than 9,000 building segments, but its masks do not provide individual building IDs. Under our 8-connected pre-event-region rule the original scene has 761 regions, with many adjacent buildings joined. We must use computed region counts rather than repeat the advertised building total as available classifier samples.

| Class | Clean original reference regions | Conservative paired comparison subset |
|---|---:|---:|
| No damage | 332 | 83 |
| Minor | 125 | 32 |
| Major | 49 | 16 |
| Destroyed | 45 | 8 |
| Total | 551 | 139 |

The clean-region rule matches the previous preparation rule: 8-connectivity, area >=16 pixels, no source-image-edge truncation, one nonzero severity class and >=95% severity coverage. It excludes 210 regions; reasons overlap: 190 mixed/missing classes, 26 border-truncated, 2 insufficient coverage, 1 small. The paired subset additionally requires a consistent feature-registration diagnostic, local fitted shift <=20% of the region's shorter box side, and consistent original/crop annotations. Reference regions are extracted once from the original, avoiding duplicated counts of original and crop copies.

The per-class post-event semantic mask has 530/378/211/215 connected components before filtering. These are an alternative description of labeled areas, not additional independent buildings. Changing to post-event class-region evaluation could retain more regions, but would be a new prespecified protocol; do not silently mix these counts with the pre-event-region protocol.

## Recommendation and remaining preparation

Prefer HaitiBRD over EBD if the external-test goal is **four-class, map-locatable earthquake reference regions**. It is not a sufficiently large severe-class benchmark to support strong major/destroyed claims by itself. The xBD held-out test remains primary, and classifier results must stay separate from automatic detection/full-pipeline results.

Before integrating it as the replacement: prepare RGB tiles on a common grid with geography retained; apply the documented palette adapter; freeze exclusions for the five conflicting crop areas; generate portable test manifests and an evaluator; update the team handoff. Preserve the original labels and report the filtered scope. Do not add this event to training/tuning or adopt author-trained damage weights.

No alternative should be described as solving all issues merely because it has four matching class names. Here the label-definition and geographic checks are positive, while severe support, semantic grouping and single-scene breadth remain limitations.
