# Team workflow

1. Pull the latest `main` before starting a task.
2. Create a branch, for example `student1/data-paths`, `student2/tiny-learning-check`, `student3/job-api`, or `student4/map-view`.
3. Work mainly in your owned files. A file owner coordinates changes; other students may contribute with review.
4. Commit small, understandable changes and push the branch.
5. Open a pull request, describe the resulting behavior and checks, and request a teammate's review.
6. Merge after review and passing checks; everyone pulls the updated `main`.

Example after the shared repository exists:

```powershell
git switch main
git pull --ff-only
git switch -c student3/job-api
# Edit and verify your changes.
git add backend tests
git commit -m "Add inference job API"
git push -u origin student3/job-api
```

Use a GitHub pull request to merge; do not have four students pushing directly to `main`. Avoid changing another student's branch or rewriting shared history. If two changes touch the same interface, agree the example record in `contracts/` first.

## Shared files

Students 1 and 2 review changes to splits, labels, preprocessing and evaluation. Students 2 and 3 agree the model inference function. Students 3 and 4 agree API payloads and the development fixture. A dependency, schema or configuration change belongs in the same PR as the code that uses it. Do not tune using HaitiBRD/EBD or change held-out membership without recording a new version.

## Checks

Run Python tests relevant to your change. Current source-only suite:

```powershell
python -m pytest tests/test_labels.py tests/test_ebd.py tests/test_external.py tests/test_detector.py -q
python scripts/check_repository.py
```

Frontend changes: `cd frontend`, `npm ci`, `npm run build`. Commit `package-lock.json` with dependency changes. GitHub Actions performs these checks; it does not download datasets/weights or train models.

Never commit data images, checkpoints, virtual environments, node_modules, local job databases or generated handoff ZIPs. Small audit metadata is deliberately retained for reproducible source selection. Verify `git diff --cached --stat` before pushing.

## GitHub setup by the project coordinator

Create an empty repository, push this folder, invite the three other students, and fill in names/handles in `docs/OWNERSHIP.md`. In repository settings, protect `main`: require a pull request, at least one approving review and passing Python/frontend checks; disallow force pushes. These settings have not been applied automatically. Add a GitHub CODEOWNERS file only after actual handles are known; ownership documentation does not itself enforce review permissions.
