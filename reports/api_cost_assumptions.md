# ARKHÉ Benchmark: API Token Cost Model & Project Budget Assumptions

## 1. Executive Summary

This document formalizes the token consumption model, pricing assumptions, and financial allocation for the **ARKHÉ Agent Boundary Defense Benchmark** under the **OpenAI Cybersecurity Grant Program (Level 2: \$20,000 USD)**.

The research measures whether trajectory-aware observability provides superior early detection of agentic boundary violations compared to isolated-event defenses. To ensure statistical significance, the benchmark scales from the 30-trajectory pilot to an expanded benchmark of **300 canonical multi-agent trajectories** across **5 boundary violation families**, evaluated over **3 independent repetitions** (2,700 total evaluations).

---

## 2. Benchmark Scale & Token Formula

### 2.1 Benchmark Dimensions
- **Number of Trajectories ($N_{\text{traj}}$):** 300
  - 5 Families $\times$ 60 trajectories each (24 Benign, 18 Near-Violation, 18 Violation).
- **Number of Detectors ($N_{\text{det}}$):** 3
  - Detector 1: Deterministic Static Pattern Baseline (Regex / static boundary matching).
  - Detector 2: Isolated Event Semantic Classifier (LLM proxy evaluating single tool calls).
  - Detector 3: ARKHÉ Trajectory Sentinel (Hybrid dynamical systems formulation + trajectory memory).
- **Stochastic Repetitions ($N_{\text{rep}}$):** 3 (to measure variance in non-deterministic LLM behavior).
- **Total Evaluations:**
  $$\text{Total Runs} = N_{\text{traj}} \times N_{\text{det}} \times N_{\text{rep}} = 300 \times 3 \times 3 = 2,700\text{ runs}$$

### 2.2 Token Consumption per Component

| Component | Model | Target Volume | Input Tokens / Call | Output Tokens / Call | Total Tokens | Base API Cost (USD) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Detector 1 (Deterministic)** | N/A (Local) | 900 runs | 0 | 0 | 0 | \$0.00 |
| **Detector 2 (Semantic Event)** | `gpt-4o-mini` | 7,200 step calls (900 runs $\times$ 8 steps) | 400 | 100 | 3,600,000 | \$1.14 |
| **Detector 3 (ARKHÉ Trajectory)** | `gpt-4o-mini` | 2,880 caution steps (40% of steps) | 1,200 | 180 | 3,974,400 | \$0.69 |
| **LLM-as-a-Judge Audit** | `gpt-4o` | 540 sampled runs (20% audit) | 2,500 | 400 | 1,566,000 | \$7.35 |
| **Dataset Synthesis & Calibration** | `gpt-4o` | 300 trajectories | 3,500 | 2,000 | 1,650,000 | \$6.67 |
| **Total Base Consumption** | - | - | - | - | **10,790,400** | **\$15.85** |

### 2.3 Research Buffer & Allocation Rationale (\$5,000 API Credits)
The base raw execution cost of single inference passes is modest (\$15.85 at modern API token rates). However, experimental research in multi-agent defensive security requires extensive iterative loops:
1. **Adversarial Red-Teaming & Prompt Perturbation:** Generating thousands of variant prompts to test guardrail robustness against evasion techniques (obfuscation, base64 encoding, persona hijacking).
2. **Hyperparameter Calibration:** Tuning risk thresholds ($\Theta_{\text{risk}}$) and weight combinations across cross-validation splits.
3. **Execution Failures & Retry Buffer:** Compensating for rate limits, API timeouts, and malformed JSON responses during autonomous evaluation.
4. **Grant Request:** **\$5,000 in OpenAI API Credits** guarantees an ample computational buffer to conduct exhaustive sensitivity analyses without token rationing.

---

## 3. Project Budget Allocation (\$20,000 USD Total)

| Budget Category | Amount (USD) | Allocation (%) | Operational Justification |
| :--- | :---: | :---: | :--- |
| **OpenAI API Credits** | \$5,000 | 25.0% | Model access for dataset synthesis, baseline evaluation, adversarial perturbation, and LLM-as-a-judge audits. |
| **Research Execution & Engineering** | \$10,000 | 50.0% | Dedicated compensation for Principal Researcher (Creúsio Adolfo Gaspar Kizua) over 6 months (~20 hrs/week) covering Milestones M1 to M4. |
| **External Security Audit & Red-Teaming** | \$3,000 | 15.0% | Independent third-party security review of dataset isolation, zero label leakage verification, and adversarial trajectory hardness. |
| **Cloud Infrastructure & Dissemination** | \$2,000 | 10.0% | Continuous benchmarking testbeds (Kubernetes / OTel collectors), artifact repository hosting, and open-access research publication fees. |
| **Total Grant Requested** | **\$20,000** | **100.0%** | **Level 2 Grant Tier (Self-contained, defensible scope).** |

---

## 4. Milestone Schedule (6 Months)

- **Month 1 (M1 - Dataset Expansion):** Synthesize and validate 300 canonical trajectories across the 5 threat families with zero label leakage verification.
- **Month 2 (M2 - Baseline Hardening):** Integrate state-of-the-art per-event guardrails (Llama-Guard 3, NeMo Guardrails, per-call GPT-4o-mini filters).
- **Month 3 (M3 - ARKHÉ Calibration):** Optimize dynamical trajectory accumulation weights on development/validation splits.
- **Month 4 (M4 - Full Benchmark Execution):** Execute 2,700 benchmark runs; compute Wilson 95% CIs and Wilcoxon paired signed-rank tests.
- **Month 5 (M5 - External Red-Teaming):** Independent third-party validation of dataset robustness and anti-leakage isolation.
- **Month 6 (M6 - Open Source Dissemination):** Publish peer-reviewed technical paper, release datasets on HuggingFace, and distribute open-source Python harness under Apache-2.0.
