# v0.4 Live Pilot — Artifact Interpretation Note

The original v0.4 pilot output files are preserved byte-for-byte as historical artifacts. Review identified aggregation defects in the original prediction JSONL files:

- `execution_time_ms`, `tokens_used`, and `max_risk_score` were serialized as zero even though the API traces and per-step predictions contain measured latency, token usage, and risk values.
- Some alert event `trajectory_id` values do not match the parent trajectory ID in the same prediction object.
- `final_outcome` is produced from the detector's own `is_flagged` prediction. It is not an observed ground-truth outcome.

Do not use those aggregate fields as zero measurements or treat the legacy `final_outcome` as ground truth. The current live runner now aggregates per-call attempt latency and tokens, derives peak risk from step predictions, emits alerts with the same opaque ID as the parent prediction, and keeps ground truth in its separate evaluator contract. This correction does not rewrite or retroactively repair the archived pilot files.

The pilot remains an exploratory single-event-baseline integration run over all v0.4 splits. Re-running the live pilot requires an API key and incurs API usage; the corrected harness has not been used to regenerate these historical results.
