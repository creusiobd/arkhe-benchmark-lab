# ARKHÉ Benchmark — Freeze Policy and Dataset Integrity

## Status of v0.4

The `v0.4_hard` files below are preserved as a legacy dataset snapshot. A live integration pilot evaluated all 50 trajectories across development, validation, and test, using only observations as model input. Because test-split predictions were produced and published, this split is **observed and exploratory**; it must not be described as an untouched, blind, or confirmatory test set. Interpretation defects in its archived aggregate prediction fields are documented in the [artifact integrity note](../results/openai_pilot_v0.4/ARTIFACT_INTEGRITY_NOTE.md); those files remain preserved unchanged.

The pilot evaluated only the single-event semantic baseline. It did not compare that baseline with the ARKHÉ trajectory detector and does not establish a reduction in false positives or generalization.

## Freeze and versioning rules

1. Do not overwrite the v0.4 dataset or its historical pilot outputs. Any correction to v0.4 requires a new dataset version and new hashes.
2. Use development for exploration and validation for model or threshold selection. Do not use a test fold to tune prompts, thresholds, detector logic, or dataset generation.
3. The planned v0.5 study uses leave-one-family-out folds. In each fold, keep the entire held-out family, including its templates and paraphrases, outside development and validation. Calibrate that fold using only its remaining families.
4. Record the dataset version, configuration hash, source commit, dirty-worktree state, model identifiers, and artifact hashes with every run.
5. After test predictions have been inspected, any test-informed change requires a new version and a newly generated evaluation sample. Never present that rerun as confirmation on an unseen test.
6. The repository is public. Family-held-out evaluation is internal and reproducible; it is not an independent external or blind audit.

## Verified SHA-256 hashes for v0.4_hard

Hashes below were recomputed from the checked-out files. The previous values in this document were stale; the dataset files were not changed by this correction.

| Dataset partition | File | SHA-256 | Trajectories | Status |
| :--- | :--- | :--- | :---: | :--- |
| Development observations | `datasets/v0.4_hard/observations/development.jsonl` | `be94f2dc2cacaa4c46043aa867ec142b6b49bcb2bf43c69da45fdd82015f5c4e` | 20 | Legacy snapshot |
| Development ground truth | `datasets/v0.4_hard/ground_truth/development_labels.jsonl` | `8982d44d19f6fad4cf529f87158701550c8c1af39e6dc237ef87e25ff6eec5c4` | 20 | Legacy snapshot |
| Validation observations | `datasets/v0.4_hard/observations/validation.jsonl` | `0d67c3eb3c5b9e43edf6a1f9fed2742bf2329d8ed692c1e4f7e26f91fab51b2b` | 10 | Legacy snapshot |
| Validation ground truth | `datasets/v0.4_hard/ground_truth/validation_labels.jsonl` | `13d6090b1e8e1e20747fd2ef4ca68fc01cb657260653a7d41b2a971961173b24` | 10 | Legacy snapshot |
| Test observations | `datasets/v0.4_hard/observations/test.jsonl` | `e28ac42367feb41bf47cf25d34780f6fee6a3e99fc36e0698cca2e203febd680` | 20 | Observed; exploratory |
| Test ground truth | `datasets/v0.4_hard/ground_truth/test_labels.jsonl` | `357047acd534ee1ac0b6c22c68a15ccf690ffcbcd6e748849be366ea770a1435` | 20 | Observed; exploratory |

## Verification

`tests/test_grant_readiness_integrity.py` compares these hashes with both the files and the diversity report. Run it with:

```bash
python -m unittest discover -s tests -p 'test_grant_readiness_integrity.py' -v
```

Any change to a listed file must update its dataset version, manifest, report, and this table together.
