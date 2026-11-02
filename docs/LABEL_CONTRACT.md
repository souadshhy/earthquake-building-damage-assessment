# Four-class label and display contract

Training: xBD. External tests: HaitiBRD and EBD, both test-only. The quantitative categories are index 0/no damage, 1/minor, 2/major, 3/destroyed. Background is excluded. A minor-to-major prediction remains an error. Original labels are retained.

EBD post-mask values 1/2/3/4 map to classifier indices 0/1/2/3; value 0 is background. Haiti's original palette is different: storage indices 1/2/3/4 mean major/no damage/minor/destroyed. Decode using the audited colors/adapter, not raw index subtraction. The source-defined scales follow xBD criteria; this is not a claim that annotation processes or reliability are identical. See `configs/label_contract.json`.

Retain all four classes from both frozen subsets. Report per-source results; optional combined results pool records and are labeled supplementary. No oversampling or destroyed-only selection. The combined counts are 1,516 no damage, 51 minor, 19 major and 14 destroyed reference regions. No user manual relabeling is required.

The map's separate presentation groups probabilities as no apparent damage=P(no damage), damaged=P(minor)+P(major), destroyed=P(destroyed). Choose its category after summing. Suggested inspection tiers remain lower/medium/high; within-tier targets tie. Keep four native probabilities/class in records. Model probabilities are not physical damage percentages, structural-safety findings or validated dispatch priorities.

Building groups/regions are accepted inspection targets and must be labeled as such. Mixed-class reference groups are not silently assigned a majority label. Reference geographic files are explicitly marked as references, not predictions; their severity labels never enter production inference inputs.

Read `EXTERNAL_TESTS.md` for the frozen membership, exclusions and limits.
