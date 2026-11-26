# Earthquake building-damage assessment

Research prototype for inspecting before/after optical imagery and displaying predicted building or building-group damage on a local map.

The backend implements validated prepared inputs and paired GeoTIFF uploads, persistent serial jobs, geographic results, crop previews and whole-job CSV/GeoJSON exports. The frontend contains a synthetic fixture map and live controls; client/API alignment remains pending. Genuine inference requires a trained provider and checkpoint, which are not supplied. No measured damage accuracy is claimed.

## Run locally

See [setup](docs/SETUP.md). Use Python 3.12 and Node 22. Run the API and frontend in separate terminals, bound to localhost. Backend health and generated API documentation are at `/health` and `/docs`.

## Source layout

- `backend/`: FastAPI validation, jobs and results.
- `frontend/`: React/TypeScript and Leaflet interface.
- `quake/`: data, model, evaluation and geography modules.
- `configs/`: dataset roles and label definitions.
- `scripts/` and `tests/`: preparation, verification and automated tests.
- `contracts/examples/result.fixture.json`: synthetic development fixture, not model output.

## Data and evaluation

Read [dataset sources](datasets/README.md), [external test definitions](docs/EXTERNAL_TESTS.md) and [label definitions](docs/LABEL_CONTRACT.md). Four native damage classes remain separate in evaluation; grouped map categories are presentation only. Model probability is not physical damage percentage or structural-safety certification.

Raw imagery, weights, training outputs, job stores, credentials and private coordination documents stay outside Git. Dataset download and redistribution terms still apply. Microsoft source attribution is retained in `quake/vendor/MICROSOFT_LICENSE`.

The backend has no authentication and is intended for localhost use only. Do not expose it publicly without a separate security/deployment review. See [contributing](CONTRIBUTING.md) for the shared-main workflow.
