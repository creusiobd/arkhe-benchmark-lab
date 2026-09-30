# ARKHÉ Anti-Leakage Model & Data Isolation Architecture

## 1. Executive Summary

A critical failure mode in security benchmarks for autonomous AI systems is **label leakage**—either direct (where ground-truth classifications or breach step indices are exposed to detection algorithms) or indirect (where metadata, scenario naming conventions, or trajectory identifiers telegraph the outcome to the detector).

The ARKHÉ Agent Boundary Defense Benchmark enforces a formal, mathematically verified **Zero-Leakage Architecture** across five defensive barriers:
1. **Physical Contract Separation**: Runtime observations and evaluation ground truth reside in mutually exclusive Pydantic schemas.
2. **Static AST Import Barrier**: Detectors are statically barred via AST audits from importing evaluation contracts or ground truth datasets.
3. **Deep Recursive Sanitization**: All incoming observation payloads are recursively validated against an exhaustive dictionary of forbidden telemetry fields.
4. **Opaque Identifier Hashing**: Trajectory identifiers are dynamically mapped to SHA-256 opaque pseudorandom hashes (`traj_<sha256[:16]>`) before reaching detectors, neutralizing heuristic cues such as `BEN`, `NEA`, or `VIO`.
5. **Decoupled Downstream Evaluation**: The execution harness operates strictly blind, emitting unannotated predictions. Evaluation occurs in an isolated downstream phase.

---

## 2. Two-Layer Canonical Contract

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      OBSERVABLE RUNTIME LAYER                           │
│                     (contracts/observation.py)                          │
├─────────────────────────────────────────────────────────────────────────┤
│ • AgentIdentity      (agent_id, role, trust_tier)                       │
│ • AgentMission       (original_mission, current_instruction)            │
│ • ToolInvocation     (tool_name, action_type, target_resource, params) │
│ • CapabilityScope    (allowed_tools, allowed_paths, allowed_hosts)      │
│ • BoundaryPolicy     (boundary_id, boundary_type, forbidden_targets)    │
│ • ToolExecutionResult(status, raw_observation)                          │
│                                                                         │
│   ❌ NO ground truth labels                                             │
│   ❌ NO breach step indices                                             │
│   ❌ NO precomputed drift or contamination scores                       │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ (Evaluated by Detectors)
                                     ▼
                     ┌───────────────────────────────┐
                     │     PREDICTION CONTRACT       │
                     │    (contracts/prediction.py)  │
                     └───────────────┬───────────────┘
                                     │ (Emits predictions.jsonl)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     EVALUATION GROUND TRUTH LAYER                       │
│                      (contracts/ground_truth.py)                        │
├─────────────────────────────────────────────────────────────────────────┤
│ • TrajectoryGroundTruth (trajectory_id, ground_truth_class,             │
│                          violation_step_index, drift_step_index,        │
│                          evaluator_rationale)                           │
│                                                                         │
│   🔒 Strictly inaccessible to Detectors and Execution Harness            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Five-Tier Anti-Leakage Enforcement Mechanism

### Tier 1: Opaque Trajectory Identifier Masking

In historical and synthetic benchmarks, trajectory IDs frequently encoded the class label (e.g., `TRAJ-TOOL-BEN-V2-008` vs. `TRAJ-SEC-VIO-V2-001`). If a detector or LLM baseline inspected the identifier string, it could achieve artificial precision without inspecting operational telemetry.

ARKHÉ benchmark runner sanitizes every trajectory at the boundary:
```python
sanitized_traj = traj.to_sanitized_opaque()
pred = det.evaluate_trajectory(sanitized_traj)
```
The method `to_sanitized_opaque()` computes:
$$\text{opaque\_id} = \text{"traj\_"} + \text{SHA256}(\text{canonical\_id})[0:16]$$
Every step within the observation is re-keyed to this opaque identifier. Detectors inspect only opaque identifiers. Canonical IDs are restored solely in the output predictions artifact to allow downstream scoring.

### Tier 2: Deep Recursive Ingestion Validator

The runtime schema executes a recursive check (`assert_no_label_leakage`) over all incoming dictionary structures, child payloads, tool parameter maps, and nested metadata:

```python
FORBIDDEN_LEAKAGE_KEYS = {
    "ground_truth_label", "label", "ground_truth_class",
    "is_attack", "attack_vector", "attack_category",
    "violation_step_index", "drift_step_index",
    "breach_step", "drift_step",
    "mission_divergence_score", "context_contamination_flag",
    "accumulated_risk_score", "human_annotation_rationale",
    "evaluator_rationale", "expected_alert", "severity"
}
```
Any attempt to instantiate a `StepObservation` or `TrajectoryObservation` containing any of these keys—even inside nested dictionaries or tool argument buffers—triggers a fatal validation error.

### Tier 3: Static AST Import Isolation

Unit tests in `tests/test_contract_separation.py` parse the Abstract Syntax Tree (AST) of every detector and harness file:
- **Rule 1**: No file in `detectors/` may import `contracts.ground_truth`, `datasets.ground_truth`, or `evaluator`.
- **Rule 2**: `harness/agent_benchmark_runner.py` may not import `contracts.ground_truth` or `evaluator`.
- **Rule 3**: `contracts/observation.py` and `contracts/prediction.py` must have zero dependencies on `contracts/ground_truth.py`.

### Tier 4: Dynamic State Inference

In ARKHÉ, detectors are forbidden from reading pre-calculated divergence or risk scores:
- **Deterministic Baselines** must pattern-match target resources against boundary policies in real-time.
- **Semantic Baselines** must classify active instructions against declared policies dynamically.
- **ARKHÉ Sentinel** computes trajectory divergence $d_{\text{mission}}(t)$, contamination belief $I_{\text{contam}}(t)$, and boundary proximity directly from raw step telemetry.

### Tier 5: Decoupled Independent Evaluator

The execution pipeline consists of two isolated executables:
1. `harness/agent_benchmark_runner.py`: Reads `datasets/observations/*.jsonl` $\to$ Emits `results/<run>/predictions.jsonl` and `execution_manifest.json`. Never touches ground truth.
2. `evaluator/evaluate.py`: Reads `results/<run>/predictions.jsonl` AND `datasets/ground_truth/*.jsonl` $\to$ Emits `benchmark_report.json`, confusion matrices, Wilson confidence intervals, and McNemar test statistics.

---

## 4. Verification and Audit

The integrity of this anti-leakage model is verified continuously via the test suite:
```bash
python -m unittest tests.test_no_label_leakage
python -m unittest tests.test_contract_separation
python -m unittest tests.test_detector_inputs
```
Any violation of this isolation model causes immediate build termination in the CI/CD pipeline.
