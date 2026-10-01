# ARKHÉ v0.5 Hard Dataset Card

## Purpose

This synthetic dataset supports a prospective, internal leave-one-family-out evaluation of trajectory-aware agent security signals. It is designed to measure the trade-off between strictly pre-violation anticipation and false alerts on hard negatives or near-violations.

It is not a representative sample of production agent traffic and must not be used to claim external generalization.

## Composition

- 120 trajectories, each containing five ordered steps.
- Three families, 40 trajectories per family: `indirect_prompt_injection`, `tool_scope_expansion`, and `secret_exposure`.
- 48 benign hard negatives, 36 near-violations, and 36 consummated violations.
- Four mechanisms per family and ten variants per mechanism.
- Task A negatives contain all benign and near-violation trajectories. Task B treats near-violations and violations as hazard-positive.

## Files

- `observations.jsonl`: detector-visible observations with opaque IDs and no ground-truth fields.
- `ground_truth/v0.5_labels.jsonl`: sealed evaluator annotations.
- `split_manifest.json`: three leave-one-family-out folds; validation is isolated by mechanism.
- `generation_manifest.json`: counts and SHA-256 hashes.

## Generation and quality controls

The corpus is generated deterministically from `configs/evaluation_protocol_v0.5.yaml` with seed `20261001`:

```bash
python scripts/generate_v05_dataset.py
python scripts/audit_v05_shortcuts.py
```

The audit inspects only the first four steps and fails if an individual declared shortcut reaches 95% Task A label accuracy. Passing this audit reduces obvious leakage risk; it does not prove that no multivariate or undiscovered shortcut exists.

## Known limitations

- All trajectories and adjudications are project-authored and synthetic.
- Several mechanisms share a common state-machine structure.
- Family-held-out evaluation is internal, not a blind third-party audit.
- Near-violations can be observationally similar to future violations before containment, creating a real forecasting/false-positive tension.
- English text and a small number of agent roles limit linguistic and operational diversity.

## License

CC BY 4.0. See `LICENSE`.

