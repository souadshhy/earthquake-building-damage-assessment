# Ownership and first handoffs

Fill in the names at the team meeting. Ownership means responsibility for delivering and reviewing work, not a restriction on collaboration.

| Role | Name / GitHub handle | Owned files |
|---|---|---|
| Student 1 — Data/evaluation | To assign | `datasets/`, `quake/data.py`, `quake/ebd.py`, `quake/crops.py`, `quake/external.py`, `quake/metrics.py`, preparation/audit/verification scripts, matching tests, `reports/data/` |
| Student 2 — Models/training | To assign | `quake/models.py`, `quake/training.py`, `quake/detector.py`, `quake/cli.py`, `quake/vendor/`, weight/detector scripts, matching tests, `reports/models/` |
| Student 3 — Backend/geography | To assign | `backend/`, `quake/geo.py`, `quake/io.py`, API/geography tests, `reports/backend/` |
| Student 4 — Frontend/integration | To assign | `frontend/`, frontend tests, `reports/frontend/` |

Shared: `contracts/`, `configs/`, `pyproject.toml`, `.github/`, root instructions and project plan. All students write their own report section. Keep dependencies centralized in `pyproject.toml` and `frontend/package.json`; do not create incompatible per-student environments in Git.

## First handoff per student

- Student 1: reproduce data paths/counts, check real before/after crops, preserve test membership and source exclusions. Give Student 2 a working loader. Later run evaluation on frozen checkpoints.
- Student 2: identify GPU/VRAM/RAM/OS, reproduce detector inference; later prove learning on a training-only tiny subset. Give Student 3 a documented inference function with model provenance.
- Student 3: agree pair/result examples with Students 2/4, implement pair validation and job API, preserve geography and generate matching exports.
- Student 4: implement map and linked list against a clearly marked fixture, then integrate actual jobs/predictions and exports with Student 3.

Shared goal: one real image pair → detected buildings/groups → trained damage predictions → suggested tiers → interactive map → CSV/GeoJSON. Integrate at least twice weekly. Current preparation does not claim that this pipeline is finished.
