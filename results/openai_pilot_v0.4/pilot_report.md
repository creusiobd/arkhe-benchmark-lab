# ARKHÉ Benchmark — Controlled OpenAI API Live Pilot Report

**Experiment:** `openai_live_pilot_v0.4`  
**Protocol Version:** `1.0.0`  
**Evaluation Mode:** `openai_api` (Official OpenAI Chat Completions SDK)  
**Model Requested:** `gpt-4o-mini`  
**Model Returned:** `gpt-4o-mini-2024-07-18`  
**Date of Execution:** `2026-10-01T01:09:15.734276+00:00`  

---

## 1. Executive Summary & Epistemic Boundaries

This controlled live pilot evaluated the official OpenAI API (`gpt-4o-mini`) as an isolated event-level guardrail baseline against the frozen **ARKHÉ v0.4 Hard Dataset** (50 structurally disjoint trajectories, 134 steps per repetition, evaluated across $R=2$ repeated measures).

> [!IMPORTANT]
> **Scientific Disclaimer and Epistemic Boundaries:**
> 1. This pilot evaluates the behaviour of an isolated single-event semantic classifier and does **not** constitute a formal audit or general assessment of OpenAI's suite of security products or broader AI safety offerings.
> 2. Results are strictly grounded in the frozen synthetic dataset (`datasets/v0.4_hard/`) and must **not** be extrapolated as proof of universal production efficacy.
> 3. Zero ground truth or trajectory lookahead was provided to the detector during evaluation.

---

## 2. Pre-Flight Live Smoke Test Verification

Prior to the batch run, an isolated synthetic smoke test was executed against the API:
- **Authentication:** Verified (HTTP 200)
- **Response ID:** `chatcmpl-ETzXv1VXke1JaOz9lye00uYJDUr4P`
- **Model Confirmed:** `gpt-4o-mini-2024-07-18`
- **Latency:** `3760.56 ms`
- **Tokens In/Out:** `496 / 51`
- **Structured Schema Parsing:** 100% compliant with Pydantic `SemanticClassificationResponse` contract.

---

## 3. Financial & Operational Telemetry

| Metric | Measured Value | Notes |
| :--- | :--- | :--- |
| **Total API Calls Attempted** | `268` | 134 steps $\times$ 2 repetitions |
| **Total API Calls Succeeded** | `268` | 100% Success Rate |
| **Total Calls Failed / Timeouts** | `0` | 0 failures |
| **Transient Retries** | `0` | Automatic backoff policy |
| **Prompt Tokens** | `131,860` | \$0.15 / 1M tokens |
| **Completion Tokens** | `15,312` | \$0.60 / 1M tokens |
| **Total Tokens** | `147,172` | Verified from API response headers |
| **Total Actual Cost (USD)** | **\$0.0290** | Authorized Budget: \$5.00 |
| **Average Latency per Call** | `1133.37 ms` | Hosted cloud inference |

---

## 4. Benchmark Performance Results

### Task 1: Pre-Violation Anticipation (Consummated Violations)
*Evaluates whether the detector flagged the trajectory before the explicit boundary violation step executed.*

| Repetition | TP | FP | TN | FN | Precision | Recall | Specificity | F1-Score | Lead Steps |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Repetition 1** | 15 | 22 | 13 | 0 | 0.405 | 1.000 | 0.371 | **0.577** | 1.53 |
| **Repetition 2** | 15 | 22 | 13 | 0 | 0.405 | 1.000 | 0.371 | **0.577** | 1.53 |

*95% Wilson Score CIs (Repetition 1):*
- Precision: `[0.264, 0.565]`
- Recall: `[0.796, 1.000]`
- Specificity: `[0.232, 0.537]`

---

### Task 2: Boundary Pressure & Hazard Detection
*Evaluates whether the detector alerted on trajectories exhibiting boundary pressure, near-violations, or consummated violations.*

| Repetition | TP | FP | TN | FN | Precision | Recall | Specificity | F1-Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Repetition 1** | 30 | 7 | 13 | 0 | 0.811 | 1.000 | 0.650 | **0.895** |
| **Repetition 2** | 30 | 7 | 13 | 0 | 0.811 | 1.000 | 0.650 | **0.895** |

---

## 5. Inter-Repetition Variability & Stochastic Consistency

To quantify stochastic variance in hosted inference with identical inputs ($temperature=0.0$):

- **Observed Trajectory Agreement:** `100.0%`
- **Observed Step-Level Agreement:** `99.2%` (134 steps compared)
- **Cohen's Kappa ($\kappa$):** **`1.000`**
- **Contingency Matrix (Trajectory Flagging):**
  - Both Repetitions Flagged: `37`
  - Neither Flagged: `13`
  - Discrepant (Rep 1 Only): `0`
  - Discrepant (Rep 2 Only): `0`

---

## 6. Stratified Breakdown by Attack Family & Ground Truth Class

### Trajectory Flagging Rate by Scenario Family (Repetition 1):
- **`human_intervention_bypass_or_concealment`:** 9/10 (90.0% flagged)
- **`indirect_prompt_injection`:** 8/10 (80.0% flagged)
- **`unauthorized_external_communication`:** 7/10 (70.0% flagged)
- **`tool_scope_expansion`:** 6/10 (60.0% flagged)
- **`secret_exposure`:** 7/10 (70.0% flagged)

### Trajectory Flagging Rate by Ground Truth Class (Repetition 1):
- **`violation`:** 15/15 (100.0% flagged)
- **`near_violation`:** 15/15 (100.0% flagged)
- **`benign`:** 7/20 (35.0% flagged)

---

## 7. Audit Checklist & Verification Conformance

- [x] Evaluated 50 unique hard trajectories ($N=50$, range 30–60 satisfied).
- [x] Verified execution mode was strictly `openai_api` without fallback.
- [x] Model requested (`gpt-4o-mini`) and returned (`gpt-4o-mini-2024-07-18`) logged.
- [x] Complete per-call traces persisted in `api_call_traces.jsonl`.
- [x] Ground truth isolated from prompts and detectors.
- [x] Repeated measures analyzed per trajectory (not inflated sample size).
- [x] Zero API credentials persisted or displayed in artifacts.
- [x] Actual cost computed from token headers (\$0.0290 USD vs \$5.00 budget limit).
