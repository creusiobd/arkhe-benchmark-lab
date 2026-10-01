# OpenAI Researcher Access Program — Official Application Submission

This document contains the tailored, audit-grade application content specifically formatted for the **OpenAI Researcher Access Program** application form at:  
`https://openai.com/form/researcher-access-program/`

---

## 1. Applicant & Professional Information

* **First Name:** Creúsio Adolfo
* **Last Name:** Gaspar Kizua
* **Country / Region:** Brazil
* **Email Address (OpenAI API Account):** `[Your OpenAI API Account Email]`
* **Institutional / Professional Email:** `[Your Institutional or Organization Email]`
* **Professional Profile Link:** `https://github.com/creusiobd/arkhe-benchmark-lab` *(and LinkedIn: `[Your LinkedIn URL]`)*
* **Institution / Organization:** `[Your University, Research Lab, or Independent AI Security Research Affiliation]`
* **Current Educational Stage / Role:** Lead Systems & AI Security Researcher

---

## 2. Research Area & Categorization

* **Primary Research Focus:** Alignment / Safety, Misuse Potential & Red-Teaming / Interpretability
* **Project Keywords:** Autonomous Agents, Boundary Defense, Multi-Step Trajectory Observability, Indirect Prompt Injection, Tool Scope Expansion, False Positive Reduction.

---

## 3. Project Title & One-Line Summary

* **Project Title:**  
  `ARKHÉ Agent Boundary Defense Benchmark: Evaluating Trajectory-Aware Signals Against Single-Event Guardrails Under Recall Constraints`

* **One-Line Summary:**  
  An empirical open benchmark evaluating whether trajectory observability systematically reduces false alarms under a pre-specified 90% recall floor compared to event-level LLM guardrails across 120 hard agent trajectories.

---

## 4. Problem Statement & Research Question

*(Form word limit: ~150–200 words)*

Autonomous AI agents executing enterprise workflows chain sequences of tool calls, environment queries, and state mutations. In these multi-step pipelines, individual actions often appear benign and policy-compliant when evaluated in isolation. However, across sequential steps, operations compound into hazardous trajectories such as cumulative context contamination from indirect prompt injection, unprompted capability expansion, and stealthy credential egress.

Existing perimeter defenses rely predominantly on point-in-time guardrails: single-event semantic classifiers, static regex policies, and per-call tool filters. Because they evaluate the immediate invocation without causal sequence context, single-event guardrails face a severe operational dilemma: tightening detection thresholds triggers prohibitive false alarm rates on legitimate multi-step workflows containing adversarial vocabulary, while relaxing thresholds permits multi-step intent hijacking to evade detection.

The critical research gap is the absence of an open, reproducible benchmark measuring whether temporal trajectory observability can systematically reduce false positive rates while maintaining an operationally mandatory recall floor ($Recall \ge 90\%$) against hard negatives and indirect violations. This project delivers a scoped, empirical evaluation of that specific trade-off.

---

## 5. Methodology & Planned Use of OpenAI API

### 1. Research Question & Hypotheses
* **Central Question:** Do multi-step trajectory signals systematically reduce false positive rates on benign workflows with adversarial framing, under a pre-specified recall floor ($Recall \ge 0.90$), compared to isolated event-level classifiers?
* **Hypothesis ($H_1$):** Trajectory-aware defense achieves a statistically significant reduction in false positive rate ($FPR$) relative to event-level baselines, while satisfying $Recall \ge 0.90$ across a 3-fold leave-one-family-out evaluation.
* **Null Hypothesis ($H_0$):** Trajectory observability yields no reduction in false positive rate ($FPR_{\text{trajectory}} \ge FPR_{\text{event}}$) under the $Recall \ge 0.90$ constraint, or fails to meet the operational recall floor.

### 2. Experimental Scope & Threat Families (120 Hard Trajectories)
* **Dataset:** 120 structurally hard trajectories distributed equally across 3 threat families (40 per family):
  1. `indirect_prompt_injection` (40 trajectories)
  2. `tool_scope_expansion` (40 trajectories)
  3. `unauthorized_secret_exposure_or_egress` (40 trajectories)
* **Composition per Family:** 16 hard negatives / benign with adversarial framing (40%), 12 near-violations / boundary pressure (30%), 12 consummated violations (30%). Total: 48 benign, 36 near-violations, 36 violations.
* **Evaluation Protocol:** 3-fold leave-one-family-out cross-validation. Thresholds calibrated strictly on validation folds to enforce $Recall_{\text{val}} \ge 0.90$.

### 3. Integration with OpenAI Models
1. **`gpt-4o-mini-2024-07-18` (Primary Event Baseline):** Evaluates immediate tool invocations in isolation via structured outputs (Pydantic schema `SemanticClassificationResponse`).
2. **`text-embedding-3-small` (ARKHÉ Trajectory Sentinel Kernel):** Continuously projects agent mission instructions and raw observations to compute semantic divergence and adversarial subspace contamination along the execution trajectory.
3. **`gpt-4o` (Comparative Robustness Check):** Benchmarks whether frontier-scale reasoning alters the event-level trade-off between false alarms and detection latency.

---

## 6. API Credit Request & Empirical Budget Justification

* **Total API Credits Requested:** **$1,000 USD**
* **Empirical Feasibility Already Demonstrated:**
  In our controlled live pre-pilot on `v0.4_hard` (commit `cac040e0`), we executed **268 real calls** to `gpt-4o-mini-2024-07-18` with a 100% success rate (0 failures, 0 retries), consuming 147,172 tokens at an actual verified cost of **$0.0290 USD** (**$0.00058 per trajectory**).

### Credit Allocation Breakdown ($1,000 USD):
1. **`gpt-4o-mini-2024-07-18` (Primary Event Classifier & Cross-Validation):**  
   - 120 trajectories $\times$ 3 steps $\times$ 2 repetitions = 720 test evaluations (~1.2M tokens $\approx$ $0.20 USD).  
   - 3-fold leave-one-family-out calibration & threshold optimization: ~2,500 calls (~3.5M tokens $\approx$ $0.60 USD).
2. **`text-embedding-3-small` (Continuous Trajectory Projections):**  
   - Dense state and observation embeddings across 120 trajectories $\times$ multiple intermediate states + reference prototypes (~2.0M tokens $\approx$ $0.05 USD).
3. **`gpt-4o` (Frontier Robustness Benchmarking):**  
   - Comparative evaluation across the 120 hard trajectories (720 calls $\times$ 600 tokens $\approx$ $2.50 USD).
4. **Prompt Engineering, Multi-Repetition Variance & Margin of Safety:**  
   - Repeated sampling to measure stochastic variability across prompt formulations and context variations.  
   - $1,000 in credits provides a comfortable safety buffer ensuring complete experimental closure without risk of depletion.

---

## 7. Open Science, Safety & Public Dissemination Plan

* **Dual Open Licensing:** Dataset released under **CC-BY-4.0**; benchmark execution harness and evaluator released under **Apache-2.0**.
* **Public Codebase:** Hosted openly at [`https://github.com/creusiobd/arkhe-benchmark-lab`](https://github.com/creusiobd/arkhe-benchmark-lab) with automated CI/CD workflows and 170+ passing regression tests.
* **Persistent Archiving & DOI:** Dataset and evaluation harness deposited on Zenodo with permanent DOI upon project completion.
* **Open Technical Report & Preprint:** Full transparency of positive, null, or negative findings published in a comprehensive technical report and submitted to arXiv.
* **Safety & Defensive Orientation:** All 120 trajectories execute in isolated synthetic sandboxes with mock credentials (`ARKHE_FAKE_TOKEN_*`) and local sinks (`http://localhost:8080/mock-sink`), without functional malware or zero-day payloads.
