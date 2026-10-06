# ARKHÉ v0.5 Evaluation Report

**Claim status:** `integration_only`

The primary endpoint is strictly pre-violation anticipation. Boundary-pressure detection is reported separately.

| Detector / run | Task A recall | Task A FPR | Task B recall | N |
|---|---:|---:|---:|---:|
| arkhe_no_contamination:repetition_1 | 94.4% (34/36) | 71.4% (60/84) | 100.0% (72/72) | 120 |
| arkhe_no_contamination:repetition_2 | 94.4% (34/36) | 71.4% (60/84) | 100.0% (72/72) | 120 |
| arkhe_no_history:repetition_1 | 88.9% (32/36) | 71.4% (60/84) | 100.0% (72/72) | 120 |
| arkhe_no_history:repetition_2 | 88.9% (32/36) | 71.4% (60/84) | 100.0% (72/72) | 120 |
| arkhe_trajectory:repetition_1 | 94.4% (34/36) | 71.4% (60/84) | 100.0% (72/72) | 120 |
| arkhe_trajectory:repetition_2 | 94.4% (34/36) | 71.4% (60/84) | 100.0% (72/72) | 120 |
| deterministic_event:repetition_1 | 100.0% (36/36) | 100.0% (84/84) | 100.0% (72/72) | 120 |
| deterministic_event:repetition_2 | 100.0% (36/36) | 100.0% (84/84) | 100.0% (72/72) | 120 |
| semantic_event:repetition_1 | 100.0% (36/36) | 100.0% (84/84) | 100.0% (72/72) | 120 |
| semantic_event:repetition_2 | 100.0% (36/36) | 100.0% (84/84) | 100.0% (72/72) | 120 |

## Interpretation limits

- The corpus is synthetic and project-authored, not an external blind benchmark.
- Three held-out families do not establish broad operational generalization.
- Repetition 2 is reported as repeatability and is not pooled as new evidence.
