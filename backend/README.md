# Student 3 — backend, geography and exports

The FastAPI service implements prepared pairs, GeoTIFF uploads, persistent serial jobs, status, geographic results, crop previews and matching CSV/GeoJSON exports. Run from the repository root with `python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload`.

Own input validation, one-at-a-time inference jobs, SQLite job metadata, disk artifacts, pixel-to-map conversion and CSV/GeoJSON exports. Reuse `quake/geo.py` and `quake/io.py`. Keep backend tests under `tests/`; write report material in `reports/backend/`.

Review `contracts/API.md` and matching examples with Students 2/4. Prepared geographic inputs come from `data/haitibrd_prepared_v1/demo_pairs.json` and valid xBD sidecars. Reference severity files are excluded from inference inputs.

Supported uploads: aligned, same-grid RGB GeoTIFF pairs up to 4096×4096. Reject absent geography/incompatible grids. Preserve per-result IDs and equal counts in the map, CSV and GeoJSON. Handle empty detections and failed inference. Do not invent EBD coordinates or use severity annotations as inference inputs.

## Run and verify

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_backend.py -q
.\.venv\Scripts\python.exe scripts/verify_backend.py --output runtime/backend_validation.json
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
```

`/docs` describes both submission encodings. `/pairs` lists validated headers and rejected pair IDs. Pixel data are checked again on submission. Startup scans local pair headers, so a large xBD registry can take several seconds. A fresh clone with no imagery returns an empty registry and still serves health/docs.

Without a configured genuine provider, health reports `inference_ready=false` and submissions return 503. Student 2 supplies the callable described in the API contract. Set it before starting the server, for example `$env:QUAKE_INFERENCE='quake.inference:provider'` once that actual module exists. Its `check_ready()` must verify/load the trained checkpoint, class order, paired mode and detector provenance. This repository currently has no such provider or trained damage checkpoint.

Runtime defaults to `runtime/backend`. Override with `QUAKE_RUNTIME` for a separate job store. One process owns a store through an OS file lock. Shutdown finishes active inference. An unexpected restart fails interrupted running jobs with a readable message and resumes queued work when a provider exists. Completed artifacts remain accessible. Use one Uvicorn worker.

Tests inject controlled inference directly into `create_app`; those outputs establish backend behavior only. No synthetic provider is enabled by the server command. Report and teammate handoffs are in `reports/backend/`.
