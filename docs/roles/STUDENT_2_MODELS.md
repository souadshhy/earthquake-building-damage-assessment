# Student 2 — models and training

Own `quake/models.py`, `quake/training.py`, `quake/detector.py`, `quake/cli.py`, `quake/vendor/`, `scripts/download_weights.py`, `scripts/verify_detector.py` and corresponding tests. Put your methods/results in `reports/models/`.

Selected: frozen Microsoft pretrained UNet pre-event branch for localization; shared ImageNet ResNet-18 before/after encoder with a four-class damage head. The checkpoint is not already trained for our damage task. Preserve vendor license/provenance; do not substitute pretrained damage outputs for our required training.

First obtain hardware specifications and reproduce the existing detector-only check. After the team begins training, run a training-only tiny learning check before the main paired and after-only experiments. Use xBD validation to select settings; neither external test may influence training, checkpoints or hyperparameters.

Agree a documented inference function with Student 3. Return pixel regions, four native probabilities and model/image provenance; geographic conversion belongs to Student 3. Connected segmentation regions may contain multiple buildings. Use `contracts/API.md` to keep field names consistent.

Save weights/logs under ignored `weights/` and `runs/`. Commit configuration and relevant source changes; share large checkpoints separately with checksums. No damage-model training or accuracy result exists in the preparation handoff.
