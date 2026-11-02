# Student 3 — backend, geography and exports

Build the FastAPI service here. `app.py` currently provides `/health` only; no real prediction/job endpoint exists yet. Run from the repository root with `python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload`.

Own input validation, one-at-a-time inference jobs, SQLite job metadata, disk artifacts, pixel-to-map conversion and CSV/GeoJSON exports. Reuse `quake/geo.py` and `quake/io.py`. Keep backend tests under `tests/`; write report material in `reports/backend/`.

First agree the records in `contracts/API.md` with Students 2/4. Keep interface examples in `contracts/examples/`. Prepared geographic input pairs are indexed by `data/haitibrd_prepared_v1/demo_pairs.json` after preparation. Reference GeoJSON contains truth labels and is not a prediction or production input.

Supported uploads: aligned, same-grid RGB GeoTIFF pairs up to 4096×4096. Reject absent geography/incompatible grids. Preserve per-result IDs and equal counts in the map, CSV and GeoJSON. Handle empty detections and failed inference. Do not invent EBD coordinates or use severity annotations as inference inputs.
