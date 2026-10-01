# v0.5 Evidence Readiness Update

## Implemented

| Grant evidence requirement | Repository evidence | Status |
|---|---|---|
| Machine-readable prospective protocol | `configs/evaluation_protocol_v0.5.yaml` plus Pydantic contract | Complete |
| Fixed 120-trajectory corpus | `datasets/v0.5_hard/` | Complete |
| Exact 48/36/36 class allocation | generation manifest and tests | Complete |
| Family-held-out folds | `split_manifest.json` | Complete |
| Mechanism-isolated validation | fold manifest and tests | Complete |
| Validation-only threshold selection | `calibration/select_threshold.py` | Complete |
| Task A / Task B separation | `evaluator/evaluate_v05.py` | Complete |
| Pre-run sensitivity statement | `reports/v0.5_power_analysis.*` | Complete |
| Shortcut/leakage audit | `reports/v0.5_shortcut_audit.json` | Complete, bounded |
| Ablation paths | no-history and no-contamination configurations | Complete |
| Freeze enforcement | `scripts/freeze_v05.py` and harness verification | Complete; current freeze is reproducibility-only |
| Live OpenAI semantic baseline | fail-fast harness path, per-call telemetry, and smoke evidence | Integration verified; fresh prospective run pending |
| External validity | independent production traces or third-party corpus | Not yet available |

## Development rehearsal finding

The unfrozen offline rehearsal is deliberately labeled test-informed and integration-only. At the validation-calibrated recall floor, the primary ARKHÉ configuration produced 34/36 pre-violation detections (94.4%) and 60/84 Task A false positives (71.4%). The deterministic and offline semantic baselines reached recall only by alerting on all 84 negatives. These numbers are not grant success claims; they expose the central research difficulty: near-violations are legitimate pressure alerts for Task B but false positives for forecasting future consummated violations in Task A.

## Live integration smoke evidence

The bounded OpenAI smoke run completed 50 successful structured calls with `gpt-4o-mini-2024-07-18`, using 25,339 input tokens and 2,901 output tokens. The operator-supplied rate calculation estimated US$0.00554145. Per-call records contain request ID, model, step index, latency, token counts, attempts, and status; they intentionally exclude prompts, observation content, and credentials. Its nine fold-level predictions are labeled `smoke_test` and `integration_only` and must not be interpreted as comparative performance evidence.

## Decision consequence

The proposal remains credible only if it promises a transparent evaluation of this trade-off, including null or negative results. It should not promise that the current detector has already reduced false positives to an operationally acceptable level. The next research step is a frozen live single-event baseline plus independent scenario review, not post-hoc tuning on the current held-out outputs.

Because v0.5 held-out outputs were inspected before the freeze, its freeze manifest is marked `reproducibility_only`. A confirmatory grant study must use a newly versioned sample whose held-out outputs have never been inspected before its prospective freeze. The harness enforces this distinction in its run status.

The frozen offline replay reproduced all 1,200 fold/detector/repetition decisions under freeze `freeze_951a80b3e6c472e39612` and was automatically labeled `frozen_reproducibility_run` / `integration_only`.
