# Student guide: understand the project before starting

This guide explains the whole project in plain language. Read it once as a team. Each student also has a separate AI handoff file in this folder.

The figures below describe the prepared handoff. If the team deliberately changes a dataset version, update the configuration and this guide together. Do not silently change the splits to obtain better results.

## 1. What are we building?

We are building a local application that helps people decide which buildings or building groups should be considered for inspection after an earthquake.

The user selects a prepared example or provides suitable satellite images of the same area: one taken before the disaster and one taken afterward. The system locates buildings, compares the before/after views, estimates visible damage and places the results on an interactive map.

The user can click a building/group, see its images and damage estimate, filter results, view counts and download CSV or GeoJSON reports. CSV is a table that opens in spreadsheet software. GeoJSON stores shapes and their locations so mapping software can read them.

The output suggests an inspection tier: high, medium or lower. This is an image-based suggestion. It does not certify a building as safe, measure hidden structural damage, or replace an inspection team.

We accept building groups as targets. For example, if touching buildings form one region in the image, the map can show that region as a building group. It must not pretend that the group is one verified individual building.

## 2. Follow one example through the system

Imagine two satellite images showing the same neighbourhood.

1. The application checks whether both images are usable and cover the same geographic grid.
2. The first AI model marks building areas in the before-event image.
3. The software turns those marked areas into regions. A region may contain one building or several touching buildings.
4. For each region, it cuts a small window from both images. These two small pictures are a paired crop.
5. The second AI model compares the crops and returns four damage probabilities.
6. The application creates a display category and suggested inspection tier.
7. Geographic information converts image positions into map positions.
8. The map, building list, counts and downloadable reports show the same result records.

This is the main integration milestone. It is not yet a completed feature in the current repository.

## 3. What type of AI are we using?

We use **supervised deep learning**. Supervised means that training examples already have reference answers, called labels. An example might show a before/after building crop with the answer “major damage.” The model makes a prediction, compares it with the answer, and adjusts its internal numbers to reduce future errors.

Deep learning means that the model contains many layers that learn useful patterns. Our models are convolutional neural networks, or CNNs. A CNN examines small image areas repeatedly. Early layers can learn patterns such as edges; later layers combine patterns into more useful image features. These features are learned numerical descriptions, not written engineering rules.

We are using two different CNN architectures for two different jobs. Neither is a decision tree or a regression model in this project.

### Model 1: UNet locates building areas

UNet performs **image segmentation**: it gives a prediction for each pixel, here building versus background. Think of its output as a mask that highlights building areas.

We use the pre-event building branch of Microsoft's pretrained Siamese UNet implementation. Pretrained means that somebody has already trained its internal numbers on imagery. Frozen means that our current plan keeps those numbers unchanged. We use only its building-localization branch, not its pretrained damage predictions.

The software groups neighbouring building pixels into regions. This explains why touching buildings can become one building group. The detector does not guarantee that each region is a separate physical building.

What is already checked: the pinned checkpoint loaded and its pre-event branch ran on one real Mexico training image. This is a technical sanity check, not proof of reliable detection everywhere. The checkpoint may have seen some xBD events during its original training; this must be disclosed when reporting detector/full-pipeline results.

Main files: quake/detector.py and quake/vendor/. Student 2 owns this work.

### Model 2: paired ResNet-18 estimates damage

ResNet-18 is a CNN architecture. The initial weights come from ImageNet, where the original model learned to recognize 1,000 everyday object categories. It was not originally trained to classify earthquake damage.

We remove that original output layer and add our own four-category damage output. We then need to train it using our labeled damage examples. This reuse of previously learned image features is called **transfer learning**.

Our version is paired, also called Siamese:

- The same ResNet-18 feature extractor examines the before crop and the after crop. It shares the same learned numbers for both images.
- It produces one feature vector for each view. A vector is simply a list of numbers describing the image.
- The new damage head receives both vectors and their absolute difference. This difference is between learned features, not a direct subtraction of raw image pixels.
- The head produces four probabilities: no damage, minor damage, major damage and destroyed.

The current code has a four-output linear head. It is written but has not been trained for our damage task. We do not yet have measured damage accuracy.

Main files: quake/models.py and quake/training.py. Student 2 owns training; Student 1 later evaluates the frozen trained model.

### What does training involve?

For each reference building, we take the same window from both views, add 20% context around each side, pad outside image boundaries and resize to 224×224. The image values are normalized using the ImageNet convention. Random flips/rotations, when used in training, must be identical in both views.

The starting plan trains the new head for three epochs with the encoder frozen, then fine-tunes for up to twenty more epochs. An epoch is one pass through the training examples. Fine-tuning means allowing the pretrained feature extractor to adjust to damage imagery.

Starting settings are AdamW, head learning rate 0.001, encoder learning rate 0.0001, weight decay 0.0001, batch size 16 if memory permits, seed 42 and stopping after five epochs without validation improvement. These settings are starting choices, not guaranteed hardware fit or accuracy. Class weights are computed from training counts only so rare classes receive more attention without changing the test set.

Before substantial training, Student 2 must confirm the laptop specifications and run a tiny training-only learning check. If the model cannot learn a few training examples, we should fix the pipeline before spending time on a full run. No such training was performed in the preparation stage.

## 4. What are the datasets?

A dataset contains images and their reference answers. An annotation describes an object/area and its label. A mask is an image whose pixel values describe buildings or damage categories.

**xBD** provides before/after optical satellite imagery, building outlines, damage labels and geographic annotations across several disasters. We use its original labels as the training and primary-test reference. Its four classes are no damage, minor damage, major damage and destroyed. Background is not a fifth damage class; unclassified severity examples are excluded.

**HaitiBRD** covers the 2010 Haiti earthquake. Its report explicitly uses xBD's four-level damage scale. It supplies one original image pair, twenty derived cropped pairs and semantic building/damage masks. The TIFF images contain geographic coordinates. Its labels were manually interpreted from satellite imagery with contributor review; they are not ground-inspection findings.

**EBD Türkiye** covers the 2023 Türkiye earthquake and documents xBD-style categories. The source archive has 944 image pairs. Labels were produced with model assistance and manual correction. We have no established geographic coordinates for its supplied PNGs, so we use it for external classification testing, not invented map placement.

### Why do we train partly on hurricanes for an earthquake application?

The available hurricane events provide many labeled examples of visible damage across all four categories. Mexico earthquake examples are also included in training. We then test transfer to different events, including Haiti and Türkiye earthquakes.

This is a practical mixed-event training design. It does not mean all disaster types look the same. Good hurricane results alone do not prove earthquake performance; that is why the earthquake tests are reported separately. Training on Mexico does not invalidate testing on Haiti or Türkiye, provided the actual examples/source areas do not leak across the split.

## 5. What does each split do?

Think of learning for an exam:

| Split | Plain explanation | May it change the model? |
|---|---|---|
| Training | Practice examples with answers; the model updates its learned numbers | Yes |
| Validation | Practice exam used to choose settings and the best saved model | No direct gradient updates, but it influences our choices |
| Test | Final exam after we freeze the model/settings | No; do not use the answers to improve that experiment |
| External test | Another exam from a different dataset/event | No; checks transfer beyond the development data |

A checkpoint is a saved set of model weights and related settings. Validation chooses the checkpoint. The test set must not choose it.

We split by **disaster event**, rather than randomly mixing neighbouring buildings across training and testing. Otherwise the model could see nearly the same source image in practice and in its final exam. Before/after pairs stay together. Crops and augmentations are made after split membership is decided.

### Our prepared xBD split

| Purpose | Events | Image pairs | Eligible building annotations |
|---|---|---:|---:|
| Training | Harvey hurricane + Michael hurricane + Mexico earthquake | 783 | 77,338 |
| Validation | Florence hurricane | 319 | 6,120 |
| Primary test | Matthew hurricane | 238 | 13,155 |

An image pair is two views of an area, not two independent samples. One pair can contain many buildings.

### Our prepared external tests

| Source | No damage | Minor | Major | Destroyed | Total reference regions |
|---|---:|---:|---:|---:|---:|
| HaitiBRD | 83 | 32 | 16 | 8 | 139 |
| EBD Türkiye | 1,433 | 19 | 3 | 6 | 1,461 |
| Optional combined result | 1,516 | 51 | 19 | 14 | 1,600 |

We retain all four classes from both audited subsets, rather than adding only destroyed examples. Every record keeps its source. Report HaitiBRD and EBD separately; a combined result is optional and supplementary. None of these examples enters training or validation.

These counts are usable **reference regions** under our preparation rules, not the datasets' advertised total buildings. We checked matching images/masks, reference labels, alignment diagnostics and duplicates. Mixed-label groups, truncated/tiny regions and other unsuitable cases are excluded according to recorded rules. Five Haiti cropped damage masks disagree with the original and their areas remain excluded from the screened subset. No labels were silently rewritten to get more samples.

Haiti has only one small source scene, even though it supplies twenty crops. Its mask storage palette also uses indices that do not equal the documented severity numbers; the audited adapter handles this. EBD uses a different encoding. Do not guess labels from raw stored integers.

Fourteen destroyed regions is a small test: it can show useful examples and measured results for those examples, but it cannot prove performance everywhere. These facts do not stop the project; they determine how honestly we describe the results.

### Where are the files?

- data/xbd_team_v1/: prepared xBD images, building records, pair records and exclusions.
- data/team_external_tests_v1/: the combined index, separate source indexes, reference GeoJSON and exclusions.
- data/haitibrd_prepared_v1/: prepared RGB images and twelve same-grid 1024×1024 geographic image pairs for future map demonstrations.
- configs/dataset_roles.json: the agreed assignment of datasets to roles.
- docs/EXTERNAL_TESTS.md: full transfer/reproduction instructions.

A **manifest** is an index, like a class register: it records which example belongs where, its label/path/source and often a checksum. It does not contain the image pixels. JSONL tables contain one record per line. A checksum is a file fingerprint used to detect changes.

Data, weights and run outputs are excluded from Git. Each laptop must obtain the images separately and generate working local paths. A fresh Git clone does not contain the large datasets.

## 6. Four classes in the model, three display categories on the map

The model always produces four probabilities. Four-class testing keeps minor and major separate, so confusing them is an error.

For the map only, the current display groups minor and major as “damaged.” Example:

| Model output | Probability |
|---|---:|
| No damage | 10% |
| Minor | 25% |
| Major | 45% |
| Destroyed | 20% |

The native prediction is major damage. For display, damaged = 25% + 45% = 70%. This means the model assigned 70% probability to either minor or major under the grouping. It does **not** mean 70% of the building is damaged. Choose the display category after summing, not by simply renaming the winning native class.

| Display category | Suggested inspection tier |
|---|---|
| Destroyed | High |
| Damaged | Medium |
| No apparent damage | Lower |

The map/list can show high first, then medium, then lower. Buildings in one tier remain tied; we have not established a reliable building-by-building ranking within a tier. A higher model confidence is not automatically worse damage. Lower priority does not mean safe. Structural urgency, occupants and access are not established by these images alone.

## 7. How will we measure whether it works?

First test the damage classifier using reference building/region locations. This answers: “Given the location, can the classifier estimate damage?” Then assess the complete detection-and-classification pipeline separately. This answers: “Can it find the targets and estimate their damage?”

A detector can miss a building even if the classifier would classify a supplied crop correctly. It can also merge buildings or detect background. Report those failures rather than hiding them inside classifier accuracy.

For classification, report precision, recall, F1, class support and a confusion matrix for all four classes. Precision asks how often predictions of a class are correct. Recall asks how many reference examples of that class were found/classified correctly. F1 balances precision and recall. Macro-F1 gives each of the four classes equal importance. Support is the number of reference examples in a class. A confusion matrix shows which classes are mistaken for which others.

Compare with a training-majority baseline and an after-only ResNet-18 trained on exactly the same xBD split. The latter tests whether using both views helps. None of these comparisons has been measured yet. Detector evaluation uses one-to-one polygon matching at IoU >=0.5, where IoU measures shape overlap. Account for region/group references and pretrained-detector event overlap when interpreting results.

## 8. What is already done, and what remains?

Prepared: dataset decisions and indexes; source audits; model code and detector sanity check; source tests; repository organization; team instructions; synthetic interface example; backend health endpoint; buildable frontend starter; GitHub check configuration.

Not done: damage training, final model results, real inference jobs, the interactive map, matching report downloads and the final report. The fixture in contracts/examples/ is invented developer data, not a model prediction. GitHub checks execute after pushing; adding their configuration is not evidence of a completed remote CI run.

## 9. Four students, one connected project

| Student | Main job | Main owned area | First handoff |
|---|---|---|---|
| 1 | Data and evaluation | datasets/, preparation scripts, data/crop/metric/external modules in quake/ | Working loaders, matching counts/paths and checked crops; later evaluation tables |
| 2 | Models and training | quake/models.py, training.py, detector.py, cli.py, vendor/ | Hardware information, detector reproduction; later trained checkpoint and inference function |
| 3 | Backend, geography and exports | backend/, quake/geo.py and io.py | Agreed API example, input/geography validation, then real jobs and matching exports |
| 4 | Frontend and integration | frontend/ | Interactive map/list/filter workflow using a marked fixture, then actual API results |

Students 1 and 2 coordinate experimental changes. Students 2 and 3 agree the inference function. Students 3 and 4 agree the API. Student 3 coordinates backend/model integration; Student 4 coordinates the demonstration. Every student writes their section in reports/. Assign actual names in docs/OWNERSHIP.md.

## 10. What do the folders represent?

| Folder/file | Meaning |
|---|---|
| README.md | Project entry point and first commands |
| docs/ | Setup, plans, responsibilities and this handbook |
| configs/ | Shared dataset and label decisions |
| datasets/ | Dataset-owner instructions, not the imagery itself |
| quake/ | Python data, AI, evaluation and geographic functions |
| backend/ | FastAPI server connecting inputs, inference jobs and exports |
| frontend/ | React/TypeScript browser interface |
| contracts/ | Agreed record/API formats and a marked synthetic example |
| scripts/ | Download, preparation and verification commands |
| tests/ | Automated Python code checks |
| reports/ | Each student's report section |
| technical_checks/ | Small source-audit evidence; large local files remain ignored |
| .github/ | Pull-request template and automated GitHub checks |
| data/, weights/, runs/, runtime/ | Local datasets, checkpoints, experiments and job outputs; not committed |

## 11. The four-week working plan

| Period | Main deliverable |
|---|---|
| First three working days | Reproduce data and hardware setup, reproduce detector, then a training-only tiny learning check when training work is requested |
| By end of week one | One genuine prediction connected to geographic output, the interactive map and a report row |
| Week two | Main paired training, after-only comparison and working application features |
| Week three | Freeze settings; held-out evaluation, separate external results and pipeline error analysis |
| Week four | Report, reproduction on another laptop, demo rehearsal and final fixes |

These are targets from kickoff, not claims that elapsed calendar time or hardware capacity has been confirmed. Hold short daily check-ins and integrate at least twice weekly. Do not wait for four isolated modules to be finished before connecting them.

## 12. How to work together in GitHub

Each student clones the same repository, creates a branch, commits their work and opens a pull request. Another teammate reviews it before merging to main. Pull merged changes frequently. Do not copy four independent versions of the whole project or push datasets/checkpoints into Git.

Shared files such as contracts/, configs/ and dependencies need coordination. Change an interface and its example together. If a source split or label rule changes, record a new version rather than overwriting results silently.

Read README.md, CONTRIBUTING.md and docs/SETUP.md for commands. Give your AI the matching AI_STUDENT file in this folder and access to the repository. Those files explain responsibilities; they do not mean the AI should immediately start training or implement everybody's work.

## 13. When is the project complete?

We need a saved/reloadable trained damage model; reproducible data and experiments; honest separate classifier and pipeline results; a real supported image pair producing geographic predictions; matching interactive-map/export counts; useful error handling; another-laptop reproduction; and the report/demo.

No specific accuracy is promised before the first baseline. The purpose is a defensible working prototype and measured results, not a claim that satellite imagery replaces civil inspection.

Sources and implementation references: [xBD paper](https://arxiv.org/abs/1911.09296), [EBD release v2](https://doi.org/10.6084/m9.figshare.25285009.v2), [HaitiBRD release](https://doi.org/10.17603/ds2-fqat-4v02), [Microsoft localization source](https://github.com/microsoft/building-damage-assessment-cnn-siamese). Source licenses/provenance must remain with the work.
