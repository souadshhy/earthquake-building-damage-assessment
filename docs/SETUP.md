# Local setup

Use Python 3.12 and a Node installation that can run the existing Vite 6 frontend (Node 22 is supported). Each student clones the same repository into their own laptop and creates their own environment. Commands below use Windows PowerShell; on Linux/macOS use `python3 -m venv .venv` and `.venv/bin/python`.

## Python

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest tests/test_labels.py tests/test_ebd.py tests/test_external.py tests/test_detector.py -q
```

Use explicit `.venv` paths if PowerShell activation is restricted. PyTorch hardware-specific installation and batch size belong to Student 2 after the training laptop is identified; no GPU fit is assumed. Source tests run on CPU and do not train.

## Backend — Student 3

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
```

Visit `http://127.0.0.1:8000/health` or `/docs`. The starter provides health only, not inference jobs. Implement real jobs and exports against `contracts/API.md`; do not present the development fixture as genuine inference.

## Frontend — Student 4

```powershell
cd frontend
npm ci
npm run dev
```

Vite prints the local address. `npm run build` checks TypeScript and builds the frontend. The Vite `/api` proxy targets the local backend at port 8000. Production deployment is outside this version's scope.

## Data and weights — Students 1 and 2

Source code/tests and the starter application need no dataset downloads. For actual preparation, training and evaluation, follow `datasets/README.md` and `docs/EXTERNAL_TESTS.md`. Transfer source imagery/archives under their terms. A fresh clone has no `data/`, `weights/`, or generated `docs/team_data_status.json`.

1. Obtain the xBD archive and EBD release/provenance, and transfer/download HaitiBRD source files as documented.
2. Run `python scripts/prepare_team_datasets.py --external suite --archive 'D:\\datasets\\train_images_labels_targets.tar'` from the repository root.
3. Run `python scripts/verify_external_suite.py`. Check the source-specific counts against the documented frozen membership.
4. Student 2 obtains detector weights using `python scripts/download_weights.py` and reproduces `python scripts/verify_detector.py` when the required data are available.

Do not copy another student's generated manifest paths and expect them to work. Generated data and path indexes stay local. Run preparation commands from the repository root; they resolve project files relative to their scripts.

Large transfer files and checkpoints are shared outside Git. Record provenance/checksums and experiment settings in the report. Do not upload restricted imagery to GitHub as a workaround.
