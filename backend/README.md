# Backend

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
```

`/health` reports inference readiness, `/docs` exposes generated HTTP documentation, and `/pairs` lists locally registered prepared imagery. A fresh clone can start without datasets and returns an empty registry. Job submission returns 503 until a genuine trained inference provider is configured. No trained provider or checkpoint is included.

The service validates aligned same-grid three-band uint8 RGB GeoTIFF uploads up to 4096 by 4096 pixels, with a 128 MiB request limit. Prepared PNG inputs require validated geography. It persists serial jobs in SQLite, produces geographic results and paired previews, and exports the whole completed job as CSV/GeoJSON. Tests use explicitly controlled predictions and do not establish model accuracy.

Runtime artifacts are ignored under `runtime/backend`; one process owns each store. Use one Uvicorn worker. Set `QUAKE_INFERENCE=package.module:provider` only after the actual trained provider exists; provider requirements are shared privately. Local prepared inputs and model weights transfer separately under their source terms.

There is no authentication. Bind to localhost; this research service is not ready for public deployment. Do not commit inputs, job stores, credentials or checkpoint files.
