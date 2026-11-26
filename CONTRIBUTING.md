# Shared-main workflow

The team works on `main`. Commit or otherwise save your own changes before pulling. Use `git pull --ff-only`, coordinate overlapping edits, and push small changes. If a push is rejected, fetch and reconcile teammate changes; do not force-push shared main during normal work.

Run relevant tests before pushing:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/check_repository.py
```

Frontend changes require `npm ci` and `npm run build` from `frontend/`; keep its package manifest and lockfile synchronized. The current frontend dependency mismatch must be corrected before a fresh `npm ci` succeeds.

Review `git diff --cached --stat` and the staged contents. Do not commit credentials, raw imagery, checkpoints, environments, job artifacts, private handoffs, AI instructions or report drafts. Coordinate interface changes privately with the affected teammate and check the actual running API at `/docs`.
