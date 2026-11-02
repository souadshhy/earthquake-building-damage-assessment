# Student 1 — data and evaluation

This folder contains source documentation, not image pixels. Local data lives under ignored `data/` and the source locations documented in `docs/EXTERNAL_TESTS.md`.

Start with `../docs/EXTERNAL_TESTS.md`, `../docs/LABEL_CONTRACT.md`, and `../configs/dataset_roles.json`. The small audit inputs needed to reproduce source selection are retained in `technical_checks/test_dataset_search/`. Raw imagery there is ignored.

Your main implementation files are `quake/data.py`, `quake/ebd.py`, `quake/crops.py`, `quake/external.py`, `quake/metrics.py`, `scripts/prepare_team_datasets.py`, `scripts/prepare_external_tests.py` and source audit/download/verification scripts. Keep matching tests under `tests/`.

First deliverable: datasets load on the training laptop, the counts match the frozen specification, crops show matching before/after areas, and exclusions/provenance are understood. Do not change splits to improve scores or tune on external tests. Keep dataset IDs in all predictions/results.

Training and evaluation are different tasks: Student 2 trains; you later evaluate their frozen checkpoint. For now prepare and verify the data. Write your data/evaluation report section in `reports/data/`.

Sources: xBD original local release; [EBD v2](https://doi.org/10.6084/m9.figshare.25285009.v2); [HaitiBRD v2](https://doi.org/10.17603/ds2-fqat-4v02). Keep original terms, labels and citations.
