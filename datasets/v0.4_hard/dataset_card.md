# Dataset Card: ARKHÉ Hard Boundary Defense Benchmark (v0.4_hard)

## 1. Summary
The `v0.4_hard` dataset is a challenging benchmark crafted to defeat naive lexical detection, template memorization, and static indicator rules. It requires detectors to evaluate operational context, declared agent capability scopes, and genuine state transitions.

## 2. Whole-Family Split Isolation
- **Development:** `INDIRECT_PROMPT_INJECTION`, `TOOL_SCOPE_EXPANSION`
- **Validation:** `SECRET_EXPOSURE`
- **Test (Held-Out):** `UNAUTHORIZED_EXTERNAL_COMMUNICATION`, `HUMAN_INTERVENTION_BYPASS_OR_CONCEALMENT`

Strictly 0% family or threat mechanism overlap exists between splits.

## 3. Hard Security Scenarios
- Benign trajectories with `[EXTERNAL_NOTE]` and adversarial vocabulary (CVE audits, security reviews).
- Hard negatives where accessing `.env` or local networking is explicitly permitted by mission scope.
- Structural violations without obvious keywords (`BREACH`, `exfiltrate`, `malicious`).
- Near-violations without `WARNED` status (autonomous safe backoff).
- Granular containment outcomes: `SUCCEEDED`, `PARTIAL`, `LATE`, `FAILED`.

## 4. Test Split Freezing Rule
The test split is permanently frozen. It must not be utilized for detector tuning, threshold calibration, or iterative prompt engineering. Any modifications after viewing test outcomes require opening a new versioned benchmark cycle (`v0.5+`).
