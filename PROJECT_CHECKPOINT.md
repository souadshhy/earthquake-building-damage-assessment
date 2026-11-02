Repository location: E:\Uni\Fourth Year\Multidisciplinary Proj\earthquake-building-damage-assessment
GitHub remote: https://github.com/souadshhy/earthquake-building-damage-assessment (private).
The old C: project path is a compatibility junction to this folder; data is physically on E:.

# Project return point — current authorized preparation

## Shared repository organization

The team now has five handbooks under `docs/handbook/`: one detailed plain-language `STUDENT_PROJECT_GUIDE.md` and four self-contained `AI_STUDENT_*.md` handoffs. Root README links them. The student guide explains models, data/splits, priorities, evaluation, ownership and workflow; each AI handoff states whole-project context, current implementation, exact owned files, ordered tasks, coordination and acceptance. This documentation work performed no training.

The user requested organizing this folder as the whole team's GitHub project. `README.md`, `CONTRIBUTING.md`, `docs/SETUP.md` and `docs/OWNERSHIP.md` are the current collaboration entry points. `backend/` has a health-only FastAPI starter; `frontend/` has a React/Vite starter, not the finished map. `contracts/` contains a draft API contract and explicitly synthetic development fixture. Each role has a report folder. `.github/` contains source-test/frontend-build CI and a PR template. Large/local data, weights, runtime files and historical artifacts are excluded from Git; small required audit inputs are retained. No commit or push has been made. The repository, rather than older ZIP snapshots, is now the team's working source of truth. Assign student names/handles before configuring enforced ownership on GitHub.

**Standing scope: preparation only. No training, including a tiny experiment, unless the user changes this instruction.** Today's goals are datasets/splits, model choices, implementation plan and four-student division. No trained damage checkpoint or accuracy result exists.

## Current authorized decision

The user approved supplementing HaitiBRD with EBD test examples. Preparation is implemented: retain all four classes from both frozen audited subsets, with mandatory separate source results and an optional combined annotation-level score. Do not selectively add destroyed samples only, oversample the test, or put these examples into training/tuning. OCD-BDA stays inactive.

- xBD train Harvey/Michael/Mexico: 783 pairs, 77,338 annotations.
- xBD validation Florence: 319 pairs, 6,120 annotations.
- xBD primary test Matthew: 238 pairs, 13,155 annotations. Native membership hashes unchanged.
- HaitiBRD external: 83/32/16/8 reference regions.
- EBD external: 1,433/19/3/6 reference regions.
- Combined optional: 1,516/51/19/14 = 1,600, in no/minor/major/destroyed order.

Active external folder: `data/team_external_tests_v1`; source IDs/groups and exclusions retained. Prepared Haiti images: `data/haitibrd_prepared_v1`, RGB before imagery resampled to post grid, original labels/selection unchanged; 12 same-grid 1024px GeoTIFF pairs are future map inputs. Severity labels are excluded from these input manifests. Reference GeoJSON is not model output. EBD coordinates remain unavailable.

Building groups/regions are accepted inspection targets. Still disclose that 14 destroyed regions is limited evidence and Haiti is one small scene; source events are not 1,600 independent scenes. Manual Haiti and model-assisted EBD label provenance differ. Haiti crop masks 16–20 remain excluded because they conflict with the original. Four-class scoring retains minor/major mistakes; the three-category map display is separate.

## Model and application status

Frozen Microsoft UNet pre-event branch selected and previously verified on one Mexico training image, without weight updates. Paired ImageNet-initialized ResNet-18 code written, untrained. Backend/API, interactive map, full training and final report remain to be implemented. Product: map of predicted buildings/groups with damage categories, suggested inspection tiers, details/filters/list/counts and CSV/GeoJSON. Within-tier targets tie; outputs are inspection suggestions, not safety certification.

## Handoff and owners

Read `docs/TEAM_PLAN.md`, `docs/EXTERNAL_TESTS.md`, `docs/LABEL_CONTRACT.md`, `configs/dataset_roles.json`, `configs/label_contract.json` and `docs/TODAY_HANDOFF.md`. Current package: `deliverables/earthquake_project_team_handoff_v3.zip`. Raw/prepared images and weights transfer separately; regenerate absolute paths on another machine as documented.

Student 1 data/evaluation; Student 2 models/training; Student 3 backend/geography/exports; Student 4 frontend/map/integration. Actual names and training-laptop hardware remain to be supplied. Future feasibility milestone: tiny training-only learning check, then one genuine prediction onto the interactive map with a downloadable report. No training today.
