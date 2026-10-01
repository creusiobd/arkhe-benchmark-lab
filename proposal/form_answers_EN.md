# Official Application Form Answers — OpenAI Cybersecurity Grant Program

This document contains the consolidated, audit-grade answers for each field of the **OpenAI Cybersecurity Grant Program** application form, in English, strictly aligned with the scoped, testable applied research protocol of the **ARKHÉ Agent Boundary Defense Benchmark**.

---

### Field 1: Project Title
**ARKHÉ Agent Boundary Defense Benchmark: Evaluating Trajectory-Aware Signals Against Single-Event Guardrails Under Pre-Specified Recall Constraints**

---

### Field 2: One-line Description
A focused empirical study and open benchmark evaluating whether multi-step trajectory signals reduce false positive rates under a pre-specified 90% recall floor compared to single-event LLM classifiers across 120 hard agent trajectories.

---

### Field 3: Problem Statement
*(Strict constraint: $\le 200$ words)*

Autonomous AI agents executing enterprise workflows chain sequences of tool calls, environment queries, and state mutations. In these multi-step pipelines, individual actions often appear benign and policy-compliant when evaluated in isolation. However, across sequential steps, operations compound into hazardous trajectories such as cumulative context contamination from indirect prompt injection, unprompted capability expansion, and stealthy credential egress.

Existing perimeter defenses rely predominantly on point-in-time guardrails: single-event semantic classifiers, static regex policies, and per-call tool filters. Because they evaluate the immediate invocation without causal sequence context, single-event guardrails face a severe operational dilemma: tightening detection thresholds triggers prohibitive false alarm rates on legitimate multi-step workflows containing adversarial vocabulary, while relaxing thresholds permits multi-step intent hijacking to evade detection.

The critical research gap is the absence of an open, reproducible benchmark measuring whether temporal trajectory observability can systematically reduce false positive rates while maintaining an operationally mandatory recall floor ($Recall \ge 90\%$) against hard negatives and indirect violations. This project delivers a scoped, empirical evaluation of that specific trade-off.

*(Word count: 171 words — Approved under the 200-word limit)*

---

### Field 4: Research Hypothesis & Methodology

#### 1. Central Research Question & Formal Hypothesis
**Core Question:** Do multi-step trajectory signals systematically reduce false positive rates on benign workflows with adversarial framing, under a pre-specified recall floor ($Recall \ge 90\%$), compared to isolated event-level classifiers?

**Hypothesis ($H_1$):** On a benchmark of 120 structurally hard agent trajectories evaluated via leave-one-family-out cross-validation, a trajectory-aware detector achieves a statistically significant reduction in false positive rate ($FPR$) relative to isolated event-level baselines, while satisfying a pre-specified minimum recall constraint of $Recall \ge 0.90$.

**Null Hypothesis ($H_0$):** Trajectory-aware observability yields no reduction in false positive rate ($FPR_{\text{trajectory}} \ge FPR_{\text{event}}$) under the $Recall \ge 0.90$ constraint, or fails to meet the operational recall floor.

#### 2. Experimental Scope & Threat Taxonomy (120 Hard Trajectories)
The study freezes an evaluation corpus of **120 hard trajectories** distributed across **three core threat families** (40 trajectories per family):
1. **`indirect_prompt_injection` (40 trajectories):** Untrusted data sources embedding prompt-mediated instructions that alter agent intent.
2. **`tool_scope_expansion` (40 trajectories):** Gradual capability escalation where the agent discovers and invokes tools outside its declared mission scope.
3. **`unauthorized_secret_exposure_or_egress` (40 trajectories):** Stealthy access, harvesting, or egress of credentials and private environment variables.

**Pre-Specified Class Stratification per Family (40 trajectories each):**
- **Hard Negatives / Benign with Adversarial Framing (16 trajectories, 40%):** Legitimate workflows containing security-relevant vocabulary, prompt injection warnings, or multi-step queries that must *not* trigger alarms. Total: 48 benign trajectories.
- **Near-Violations / Boundary Pressure (12 trajectories, 30%):** Trajectories approaching boundary limits (e.g., failed probes, reading adjacent non-sensitive metadata) without consummating an unauthorized action. Total: 36 near-violations.
- **Consummated Boundary Violations (12 trajectories, 30%):** Explicit, unauthorized security breaches executed across sequential steps. Total: 36 violations.

#### 3. Evaluation Protocol: Internal Leave-One-Family-Out Cross-Validation
Because the corpus comprises three threat families, generalization across mechanisms is evaluated via a **3-fold leave-one-family-out cross-validation**:
- **Fold 1:** Test = Family 1 (40 trajectories); Dev/Val = Families 2 & 3 (80 trajectories).
- **Fold 2:** Test = Family 2 (40 trajectories); Dev/Val = Families 1 & 3 (80 trajectories).
- **Fold 3:** Test = Family 3 (40 trajectories); Dev/Val = Families 1 & 2 (80 trajectories).

**Protocol Guarantees:**
- **Strict Family Disjointness:** No decision, threshold, prompt, or parameter for a test fold is calibrated using data or labels from the held-out family.
- **Internal Evaluation Disclosure:** This protocol constitutes an internal held-out family benchmark created by the project, not an independent external audit.
- **Aggregated Testing:** Each of the 120 trajectories appears in the test partition exactly once across the aggregated evaluation ($N = 120$).
- **Development vs. Validation Split:** Within the training families, trajectories are partitioned into development and validation by clustering templates and paraphrases to prevent mechanism leakage.

#### 4. Reference Detectors
1. **Baseline 1 (Deterministic Event Rule Baseline):** Regex patterns, keyword filters, and forbidden target lists evaluating only the immediate tool call.
2. **Baseline 2 (Semantic Event Classifier Baseline):** Single-step LLM classifier querying a versioned OpenAI model (`gpt-4o-mini-2024-07-18`) with Pydantic structured output (`SemanticClassificationResponse`) evaluating immediate actions in isolation without trajectory history.
3. **Primary Detector (ARKHÉ Trajectory Sentinel):** Trajectory-oriented detector using a continuous embedding subword projection and a positive-definite quadratic Lyapunov matrix energy function $V(\mathbf{x}_t) = \mathbf{x}_t^T \mathbf{P} \mathbf{x}_t$ tracking cumulative state divergence and boundary approach velocity across sequential steps.
4. **Optional Robustness Analysis:** A secondary OpenAI model (`gpt-4o`) will be evaluated as an optional robustness check, strictly conditional on project schedule, budget, and API access limits.

#### 5. Pre-Specified Decision Rule & Metrics
1. **Threshold Calibration:** Operating thresholds for all detectors are chosen exclusively on the validation sets to satisfy the operational recall floor:
   $$Recall_{\text{val}} \ge 0.90$$
2. **Primary Metric (Test Set):** False Positive Count ($FP$) and False Positive Rate ($FPR = \frac{FP}{FP + TN}$) on the aggregated test set ($N=120$, 48 benign trajectories), conditioned on satisfying $Recall_{\text{test}} \ge 0.90$.
3. **Non-Compliance Reporting:** Detectors failing to achieve $Recall \ge 0.90$ on the test set are explicitly flagged as failing the operational safety floor.
4. **Secondary Metrics:** Precision, Recall, F1-Score, Mean Lead Steps ($N_{\text{lead}}$), Mean API Latency (ms), and Inference Cost (USD).
5. **Statistical Testing:** Paired two-tailed McNemar test on discordant pairs across the 48 hard negative benign trajectories; Wilson score 95% confidence intervals grouped by unique trajectory ($N=120$). Repeated API queries are modeled as repeated measures, not independent sample units.

---

### Field 5: Deliverables & Expected Outcomes

All grant deliverables are public, open-source, and verifiable:

1. **Open Hard Benchmark Dataset (v0.5):**
   - 120 structurally hard agent trajectories in JSONL format, fully labeled with ground truth annotations (classes, breach steps, containment attempts, and final outcomes).
   - Accompanied by a comprehensive Dataset Card, templates catalog, provenance manifest, and dual-licensing (Dataset: **CC-BY-4.0**).
2. **Reproducible Benchmark Harness & Independent Evaluator:**
   - Python testbed (licensed under **Apache-2.0**) with strict architectural separation between observable agent traces (`StepObservation`) and ground truth (`TrajectoryGroundTruth`).
   - Automated 1-click reproduction scripts (`reproduce_dataset_generation.sh` / `.ps1`) and continuous CI workflow on GitHub Actions.
3. **Public Technical Report:**
   - Transparent publication of empirical findings—documenting positive, null, or negative results regarding whether trajectory signals reduce false positives under the 90% recall floor.
4. **Open-Access Scientific Preprint:**
   - Formal manuscript submitted to arXiv / Zenodo detailing the leave-one-family-out methodology, statistical tests, and trade-offs observed (submitted as an open preprint without asserting journal acceptance).
5. **Responsible Disclosure & Limitations Dossier:**
   - Explicit documentation of threat model boundaries, synthetic data constraints, and guidelines preventing the weaponization of benchmark scenarios.
6. **Optional Trajectory Visualizer (Stretch Goal):**
   - Interactive terminal or web-based UI visualizer for inspection of state-space trajectories, implemented only if milestone deadlines permit without impacting core evaluation.

---

### Field 6: Defensive Orientation & Safety

The project is exclusively defensive in purpose, architecture, and deployment:
* **Strictly Synthetic & Sanitized Environment:** All 120 trajectories use mock credentials (`ARKHE_FAKE_TOKEN_DO_NOT_USE_*`) and local simulated sinks (`http://localhost:8080/mock-sink`). No real-world infrastructure, production databases, or live secrets are touched.
* **No Weaponized Payloads:** Prompts and observations model behavioral and telemetry signatures of prompt injection and capability expansion; they contain no zero-day exploits, executable malware, or weaponized exploit chains.
* **Direct Defensive Utility:** Enables security practitioners and frontier lab safety teams to quantify the exact false positive trade-offs of runtime agent guardrails before deploying autonomous workflows with tool-calling capabilities into production.

---

### Field 7: Work Plan & Timeline (8 Weeks)

The project is structured into an intensive, 8-week execution plan with concrete weekly milestones:

```
[Weeks 1–2] Protocol, Pre-Registration & Scope Freeze
     └── Milestone 1: Registered protocol, frozen taxonomy & statistical analysis plan.
[Weeks 3–4] Dataset Curation, Synthesis & Non-Leakage Validation
     └── Milestone 2: 120 hard trajectories generated with deterministic CI checks.
[Weeks 5–6] Controlled Leave-One-Family-Out Execution & Live API Baselines
     └── Milestone 3: 3-fold evaluation executed with gpt-4o-mini; traces & cost logged.
[Weeks 7–8] Statistical Analysis, Public Report & Preprint Dissemination
     └── Milestone 4: Paired McNemar tests, open dataset release & arXiv preprint.
```

* **Weeks 1–2 (Milestone 1 — Protocol Pre-Registration & Scope Freeze):**
  - Finalize formal statistical plan, freeze the 90% recall floor ($R_{\min} = 0.90$), and specify exact leave-one-family-out data splits.
  - *Verifiable Output:* Versioned YAML protocol and frozen analysis specification committed to repository.
* **Weeks 3–4 (Milestone 2 — Dataset Curation, Hard Negatives & Anti-Leakage Audit):**
  - Author and programmatically synthesize 120 hard trajectories across the 3 families (48 hard negatives, 36 near-violations, 36 violations).
  - Verify deterministic reproduction (100% SHA-256 match) and run AST anti-leakage validators.
  - *Verifiable Output:* `datasets/v0.5_hard/` with 120 trajectories, dataset card, and CI passing with zero failures.
* **Weeks 5–6 (Milestone 3 — Controlled Live Evaluation & Baseline Execution):**
  - Execute 3-fold leave-one-family-out cross-validation. Calibrate detection thresholds on validation folds to satisfy $Recall \ge 0.90$.
  - Run live API evaluations against `gpt-4o-mini-2024-07-18` across 2 repeated measures per trajectory. Record complete per-call traces, tokens, latency, and costs in `api_call_traces.jsonl`.
  - Conduct optional secondary robustness evaluation with `gpt-4o` if schedule and budget allow.
  - *Verifiable Output:* Frozen predictions for all 3 folds, full API traces, and verifiable cost report.
* **Weeks 7–8 (Milestone 4 — Statistical Evaluation, Open Release & Preprint):**
  - Execute independent evaluator across the 120 held-out trajectories. Compute paired McNemar test, Wilson score 95% CIs, and Cohen's Kappa inter-repetition consistency.
  - Deposit dataset and code to Zenodo/HuggingFace with permanent DOI; publish technical report and upload preprint to arXiv.
  - *Verifiable Output:* Public GitHub release (Apache-2.0), Zenodo DOI, and published arXiv preprint.

---

### Field 8: Budget Breakdown & Justification

The total grant request is **$10,000 USD**, strictly partitioned into verified inference credits and direct research support:

| Budget Item | Allocation | Cost Basis & Calculation | Verifiable Milestone Output |
| :--- | :---: | :--- | :--- |
| **OpenAI API Inference Credits** | **$1,500** | • **Model:** `gpt-4o-mini` ($0.15/1M input, $0.60/1M output).<br/>• **Volume:** 120 trajectories $\times$ 3 steps $\times$ 2 repetitions = 720 test calls.<br/>• **Cross-Validation & Dev/Val Calibration:** ~2,500 calls total $\approx$ 1.4M tokens (~$0.25 USD).<br/>• **Optional `gpt-4o` Robustness Run:** 720 calls $\times$ 560 tokens $\approx$ $1.50 USD.<br/>• **Safety Margin & Iteration:** $1,500 in credits covers prompt iterations, hyperparameter tuning, and extended token contexts with a 10$\times$ buffer. | `api_call_traces.jsonl`, `cost_report.json` with token headers and zero offline fallback. |
| **Applied Research & Engineering Stipend** | **$8,000** | • **Rate:** $1,000 / week across 8 weeks dedicated effort.<br/>• **Effort:** 100% focused technical delivery by Principal Researcher: dataset authoring (120 trajectories), leave-one-family-out harness engineering, Lyapunov kernel calibration, and statistical reporting. | Milestones 1, 2, 3, and 4; 156+ passing automated tests, open source codebase. |
| **Infrastructure, CI/CD & Open Access Deposit** | **$500** | • Cloud execution runners for sandboxed agent environments, Zenodo DOI registration, and persistent dataset hosting. | Public Zenodo DOI, active GitHub Actions CI workflow. |
| **Total Requested Funding** | **$10,000** | **$1,500 in API Credits + $8,500 in Direct Research/Infra Support** | Complete public benchmark delivery in 8 weeks. |

*Note on Prior Empirical Verification:* In pre-pilot live validation on `v0.4_hard` (commit `cac040e0`), 268 real calls to `gpt-4o-mini-2024-07-18` were executed with 100% success rate (0 failures, 0 retries), consuming 147,172 tokens at an actual verified cost of $0.0290 USD ($0.00058 per trajectory). The budget requested above is grounded in empirically measured unit economics.

---

### Field 9: Applicant Background & Execution Capacity

**Principal Researcher: Creúsio Adolfo Gaspar Kizua (São Paulo, Brazil)**
* **6+ years of practical engineering experience** in high-throughput transactional architectures, mission-critical infrastructure, and distributed telemetry.
* **Technical Lead of an engineering team of 13 engineers** maintaining 24×7 financial and banking production environments under strict regulatory standards (Central Bank of Brazil BACEN Resolution 85/2021 and PCI-DSS v4.0).
* **Technical governance and observability across 33 production APIs**, specialized in telemetry instrumentation (OpenTelemetry, Prometheus, Kubernetes, Grafana).
* **Creator of the ARKHÉ Benchmark Repository:** Designed and implemented the complete open-source codebase, including:
  - Continuous embedding subword projection and positive-definite quadratic Lyapunov matrix risk functions in `detectors/arkhe_trajectory.py`;
  - Fail-fast live OpenAI API integration with Pydantic structured schemas in `detectors/clients/openai_semantic_client.py`;
  - Hermetic anti-leakage architectural contracts separating observable step traces from sealed ground truth;
  - Deterministic dataset generation with canonical cryptographic trajectory IDs.

---

### Field 10: Open Source Commitment & Reproducibility

* **Permissive Open Source Licensing:** Codebase licensed under **Apache-2.0**, dataset licensed under **CC-BY-4.0**.
* **Audit-Grade Codebase:** Currently features **156 passing automated tests** in the continuous test suite (`tests/`), enforcing contract separation, deterministic generation invariance, Lyapunov energy convergence, and zero label leakage.
* **Empirical Grounding of Existing Pilot:**
  - *Offline Baseline (`v0.3`):* 65 trajectories evaluated under hermetic proxy mode.
  - *Live OpenAI Pilot (`v0.4_hard`):* 50 trajectories (134 steps) evaluated live across 2 repeated measures (268 calls) against `gpt-4o-mini-2024-07-18` (147,172 tokens, $0.0290 USD, 0 failures, 100% inter-repetition trajectory agreement, $\kappa = 1.000$).
* **What Remains Unknown (To Be Tested Under Grant Funding):**
  - Whether trajectory observability maintains lower false positive rates under a strict $Recall \ge 0.90$ constraint when evaluated on 120 structurally hard trajectories across held-out threat families (leave-one-family-out cross-validation).
  - The degree to which trajectory-level Lyapunov stability generalizes to previously unseen prompt injection and scope expansion mechanisms without post-hoc threshold tuning.
