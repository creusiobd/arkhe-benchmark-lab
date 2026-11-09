# ARKHÉ v0.5 Hard Dataset Card

## Purpose and evidence status

This synthetic dataset was originally designed for a prospective internal leave-one-family-out evaluation. Because test-family outputs were inspected during implementation, it is now a **development and reproducibility corpus**, not an untouched confirmatory holdout.

It measures the engineering trade-off between strictly pre-violation anticipation and false alerts on hard negatives or near-violations. It is not representative of production traffic and must not support external-generalization claims.

## Composition

- 120 five-step trajectories.
- Three families with 40 trajectories each: `indirect_prompt_injection`, `tool_scope_expansion` and `secret_exposure`.
- 48 benign hard negatives, 36 near-violations and 36 violations.
- Four mechanisms per family and ten variants per mechanism.

## Files

- `observations.jsonl`: detector-visible observations with opaque IDs and no ground-truth fields.
- `ground_truth/v0.5_labels.jsonl`: evaluator annotations.
- `split_manifest.json`: leave-one-family-out folds with mechanism-isolated validation.
- `generation_manifest.json`: counts and SHA-256 hashes.

## Quality controls

```bash
python scripts/generate_v05_dataset.py
python scripts/audit_v05_shortcuts.py
```

The declared shortcut audit fails when a single feature reaches 95% Task A label accuracy. Passing reduces obvious leakage risk; it does not prove the absence of multivariate or undiscovered shortcuts.

## Known limitations

- All trajectories and adjudications are project-authored and synthetic.
- Test-family outputs have already been observed.
- Several mechanisms share a common state-machine structure.
- Evaluation is internal, not a blind third-party audit.
- English text and a small role set limit diversity.
- v0.5 results are always `integration_only`.

## License

CC BY 4.0. See `LICENSE`.
