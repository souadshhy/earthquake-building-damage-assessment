# Earthquake building-damage inspection project

GitHub repository: [souadshhy/earthquake-building-damage-assessment](https://github.com/souadshhy/earthquake-building-damage-assessment) (private; team members need access).

Shared repository for the four-student project. Build a local interactive map of buildings/building groups, predicted damage, suggested inspection tiers and downloadable CSV/GeoJSON reports.

**Current state:** datasets/splits and model choices are prepared. Detector-only inference was checked. The damage classifier is untrained. The backend and frontend contain starter code; the prediction pipeline and interactive map still need implementation. No accuracy result is claimed.

## Student and AI guides

Everyone first reads the [plain-language project guide](docs/handbook/STUDENT_PROJECT_GUIDE.md). Then give your own AI the file for your role, together with access to this repository or the relevant files:

- [Student 1 AI handoff — data/evaluation](docs/handbook/AI_STUDENT_1_DATA_EVALUATION.md)
- [Student 2 AI handoff — models/training](docs/handbook/AI_STUDENT_2_MODELS_TRAINING.md)
- [Student 3 AI handoff — backend/geography](docs/handbook/AI_STUDENT_3_BACKEND_GEOGRAPHY.md)
- [Student 4 AI handoff — frontend/integration](docs/handbook/AI_STUDENT_4_FRONTEND_INTEGRATION.md)

The AI handoffs explain the whole project, the assigned files, first tasks, handoffs and boundaries. State your immediate task when providing the file; attaching it alone is not a request to launch training.

## Where each student works

| Owner | Main folders/files | Start here |
|---|---|---|
| Student 1 — Data and evaluation | `datasets/`, data preparation scripts, `quake/data.py`, `quake/ebd.py`, `quake/crops.py`, `quake/external.py`, `quake/metrics.py`, related tests | [Data work](datasets/README.md) |
| Student 2 — Models and training | `quake/models.py`, `quake/training.py`, `quake/detector.py`, `scripts/download_weights.py`, `scripts/verify_detector.py` | [Model work](docs/handbook/AI_STUDENT_2_MODELS_TRAINING.md) |
| Student 3 — Backend, geography and exports | `backend/`, `quake/geo.py`, backend tests | [Backend work](backend/README.md) |
| Student 4 — Frontend and integration | `frontend/`, frontend tests | [Frontend work](frontend/README.md) |
| Shared — agree changes together | `contracts/`, `configs/`, `pyproject.toml`, `.github/` | [Ownership and handoffs](docs/OWNERSHIP.md) |

Each student writes their own section in `reports/`. Assign actual student names in [OWNERSHIP.md](docs/OWNERSHIP.md). Keep code in one repository; do not make four independent project copies.

```text
backend/           FastAPI service — Student 3
frontend/          React/TypeScript browser application — Student 4
quake/             Python data, model, inference and geography modules
datasets/          Source register and data-owner instructions (no imagery)
contracts/         Agreed API/record interfaces and synthetic development example
configs/           Shared label and dataset-role decisions
scripts/           Preparation, downloads and verification commands
tests/             Python tests
docs/              Setup, team plan, ownership and dataset instructions
reports/           One report section per student
.github/           Pull-request template and automated checks
data/ weights/ runs/  Local ignored data, weights and experiment outputs
```

## Start working

Read [SETUP.md](docs/SETUP.md) for exact commands. Quick start from the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest tests/test_labels.py tests/test_ebd.py tests/test_external.py tests/test_detector.py -q
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
```

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

The starter page shows that no assessment is loaded. `/health` confirms the backend is running. Neither generates predictions. Development servers bind to this laptop only by default.

## Data and models

- xBD train: Harvey + Michael + Mexico; validation: Florence; primary test: Matthew.
- External tests: HaitiBRD and EBD, reported separately. Optional combined subset: 1,600 reference regions, including 14 destroyed.
- Four damage classes remain distinct in quantitative evaluation. Three-category grouping is a separate map presentation.
- Selected models: frozen Microsoft pre-event UNet and a shared-encoder paired ResNet-18 initialized from ImageNet.

Read [EXTERNAL_TESTS.md](docs/EXTERNAL_TESTS.md), [LABEL_CONTRACT.md](docs/LABEL_CONTRACT.md) and [TEAM_PLAN.md](docs/TEAM_PLAN.md). Datasets, prepared images, weights and training runs are **not in Git**. Transfer/download them separately and regenerate machine-local paths. Frontend/backend setup and source tests do not require the datasets. Training happens later, after hardware/data feasibility checks.

## GitHub workflow

Each student uses a branch and opens a pull request; changes are reviewed before merging to `main`. See [CONTRIBUTING.md](CONTRIBUTING.md). Pull merged changes frequently and integrate at least twice weekly.

The private repository is published. The coordinator adds the other students in GitHub Settings → Collaborators. Each student accepts the invitation, then clones it:

```powershell
git clone https://github.com/souadshhy/earthquake-building-damage-assessment.git
cd earthquake-building-damage-assessment
```

Follow docs/SETUP.md, create your own branch, and use pull requests. Large datasets and weights transfer separately. Branch protection and actual student handles still need configuration by the coordinator.

The GitHub repository is the shared working source of truth. Third-party Microsoft source retains its license in `quake/vendor/MICROSOFT_LICENSE`; dataset and imagery terms remain separate. No license for original student code is assumed here.
