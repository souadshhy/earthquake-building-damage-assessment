# Today's handoff — preparation only

**Repository update:** work from the shared repository and start with root `README.md`, `CONTRIBUTING.md`, `docs/SETUP.md` and `docs/OWNERSHIP.md`. The v3 ZIP mentioned below is a historical handoff snapshot. Backend health-only and frontend starter code now exist; real inference/API jobs and the interactive map remain team work.

No training today, including tiny experiments. The selected models remain frozen Microsoft pre-event UNet and an untrained paired ImageNet ResNet-18 damage classifier. API/map integration and real trained predictions remain future team work.

## Current datasets

Train xBD Harvey/Michael/Mexico: 783 pairs / 77,338 annotations. Validation Florence: 319 / 6,120. Primary test Matthew: 238 / 13,155. Membership hashes remain unchanged.

External HaitiBRD: 139 regions (83/32/16/8). External EBD: 1,461 (1,433/19/3/6). Class order is no damage/minor/major/destroyed. Optional combined set: 1,600 regions, including 14 destroyed. All four classes are retained from both sources. Both datasets stay outside training/tuning; source-specific reporting is mandatory.

Active indexes: `data/team_external_tests_v1`. Prepared geographic inputs: `data/haitibrd_prepared_v1`, including 12 aligned RGB GeoTIFF pairs. Reference GeoJSON is not a prediction or an inference input. EBD has no established coordinates. Raw images and weights are excluded from the handoff ZIP and must be transferred separately.

## Who does what

1. Student 1 — Data/evaluation: start with `docs/EXTERNAL_TESTS.md`, `scripts/prepare_external_tests.py`, `quake/external.py` and the dataset indexes. Reproduce paths/counts, check crops; later evaluate Student 2's frozen checkpoints.
2. Student 2 — Models/training: confirm hardware, reproduce detector check; later tiny training-only learning check and full training. Do not train or select checkpoints on external tests.
3. Student 3 — Backend/geography: validate prepared Haiti pairs and xBD sidecars; build jobs/API and consistent GeoJSON/CSV exports.
4. Student 4 — Frontend/integration: interactive map of buildings/groups, click details, linked list, category/tier filters, counts and downloads. Integrate with Student 3 early.

Use `docs/TEAM_PLAN.md`, `docs/EXTERNAL_TESTS.md` and `deliverables/earthquake_project_team_handoff_v3.zip`. Older ZIPs are historical. Assign names and get training-laptop specifications. The future joint milestone remains a real pair → detected regions → trained damage predictions → suggested tiers → interactive map → downloadable report.
