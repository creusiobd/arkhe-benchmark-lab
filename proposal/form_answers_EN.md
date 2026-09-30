# Official Submission Form Answers — OpenAI Cybersecurity Grant Program

This document provides consolidated, audited answers for all submission fields of the **OpenAI Cybersecurity Grant Program**, in English.

---

### Field 1: Project Title
**ARKHÉ Agent Boundary Defense Benchmark: Empirical Evaluation of Trajectory-Aware Observability Against Multi-Agent Boundary Violations**

---

### Field 2: One-Line Description
An open-source defensive benchmark to evaluate whether trajectory-aware observability detects mission drift, indirect prompt injection propagation, and boundary violations in multi-agent systems before isolated-event security guardrails.

---

### Field 3: Problem Description (Problem Statement)
*(Strict constraint: $\le 200$ words)*

Autonomous AI agents execute complex corporate tasks by chaining dozens of tool invocations, external context retrievals, and inter-agent delegations. In these workflows, each single action may appear benign, legitimate, and fully compliant with access control policies when inspected in isolation. However, in sequence and over time, these individually safe operations can construct an unsafe execution trajectory.

Contemporary defensive mechanisms — such as per-call LLM guardrails, atomic semantic filters, and static API blocklists — suffer from temporal blindness. They evaluate each tool invocation at a single point in time, oblivious to the underlying causal chain: silent mission drift initiated by untrusted data, the progressive accumulation of contaminated context, and subtle boundary probing.

This atomic approach creates a critical vulnerability: agents suffer intention hijacking and privilege escalation unnoticed, triggering alarms only after sensitive data exfiltration or policy violation has already occurred. The central problem is the lack of standardized, open-source benchmarks that quantitatively measure whether trajectory-aware observability can anticipate boundary violations with statistically significant lead time and reduced false positives compared to isolated-event defenses.

*(Word count: 172 words — Strictly compliant with $\le 200$ words limit)*

---

### Field 4: Research Hypothesis & Methodology
**Central Hypothesis:** Distributed weak signals across an agent's execution sequence — unvetted context contamination, dynamic objective divergence ($\Delta M$), capability expansion, and post-containment behavioral persistence — enable the detection of agentic security violations at least 1 to 2 steps before explicit breach consummation, while maintaining lower false positive rates on benign/exploratory tasks than isolated-event semantic guardrails.

**Experimental Design & Anti-Leakage Isolation:**
To prevent circularity, the benchmark enforces two strictly isolated architectural layers:
1. *Observable Runtime Contract (`StepObservation`):* Provided to detectors step by step, containing only runtime signals (identity, declared mission, sanitized action, capabilities, boundary policy, and raw tool output). No precalculated risk or drift scores exist in this contract.
2. *Reserved Ground Truth (`TrajectoryGroundTruth`):* Stored separately for blind evaluation only, recording true class, exact violation step, and human causal rationale.

**Scope & Statistical Protocol:**
The benchmark evaluates 300 canonical trajectories across 5 threat families over 3 stochastic repetitions (2,700 total evaluations). Primary metrics include median anticipatory lead time ($N_{\text{lead}}$), F1-Score, Wilson score 95% confidence intervals, and two-tailed paired Wilcoxon signed-rank tests ($p < 0.01$) to reject the null hypothesis.

---

### Field 5: Deliverables & Expected Outcomes
1. **Canonical Open Dataset (300 Trajectories):** Standardized JSONL format across 5 threat families, CC-BY-4.0 licensed, deposited on Zenodo (with DOI) and HuggingFace.
2. **Open-Source Evaluation Harness (Apache-2.0):** Modular Python framework with AST-based anti-leakage audits and multi-backend support.
3. **Three Auditable Baseline Detectors:** Deterministic regex baseline, per-event semantic classifier (`gpt-4o-mini` proxy), and the *ARKHÉ Trajectory Sentinel*.
4. **Peer-Reviewed Technical Paper & Report:** Comprehensive methodology, dynamical systems mathematical formulation, and statistical significance analysis.
5. **Interactive Trajectory Visualizer:** Web-based tool enabling step-by-step forensic replay of context contamination and mission divergence.

---

### Field 6: Defensive Orientation & Safety (Why Strictly Defensive)
This project is exclusively defensive:
* **Strictly Synthetic Data:** All scenarios utilize mock credentials (`ARKHE_FAKE_TOKEN_DO_NOT_USE_*`) and local network sinks (`http://localhost:8080/mock-sink`), completely decoupled from live infrastructure.
* **No Functional Exploits:** Scenarios evaluate high-level behavioral divergence and multi-step intention drift; no functional zero-day exploit payloads are developed or disseminated.
* **Defensive Objective:** Provides security teams with empirical criteria to calibrate guardrails and implement early-warning trajectory defenses against indirect prompt injection and privilege escalation.

---

### Field 7: Work Plan & Timeline (6 Months)
* **Month 1 (M1 — Dataset Synthesis & Anti-Leakage Audit):** Expand dataset to 300 trajectories with automated AST import isolation tests.
* **Month 2 (M2 — Baseline Hardening & API Integration):** Connect OpenAI API endpoints and establish competitive per-event baselines.
* **Month 3 (M3 — ARKHÉ Sentinel Calibration):** Calibrate dynamical trajectory weights ($w_m, w_c, w_b, w_s, w_h$) on development/validation splits.
* **Month 4 (M4 — Full Benchmark Execution):** Execute 2,700 evaluation runs, computing Wilson 95% CIs and Wilcoxon paired tests.
* **Month 5 (M5 — Independent Red-Teaming):** Third-party security review of synthetic dataset quality and anti-leakage contracts.
* **Month 6 (M6 — Open-Source Release & Paper Publication):** Publish codebase on GitHub under Apache-2.0, deposit dataset on Zenodo/HuggingFace with DOI, and release technical paper.

---

### Field 8: Detailed Budget & Justification (Level 2: \$20,000 USD)
**Grant Level: Level 2 — \$20,000 USD (Self-Contained Research Scope)**

1. **OpenAI API Credits — \$5,000 (25.0%):**
   * Direct execution cost for 2,700 benchmark runs and dataset synthesis: ~10.8M tokens (~$15.85 raw API cost at modern rates).
   * Remainder provides necessary contingency buffer for iterative prompt engineering, adversarial perturbation scans, hyperparameter tuning, and GPT-4o qualitative audits.
2. **Research Execution & Engineering Stipend — \$10,000 (50.0%):**
   * Dedicated compensation for Principal Investigator Creúsio Adolfo Gaspar Kizua over 6 months (~20 hrs/week) covering Milestones M1 to M4.
3. **External Security Audit & Red-Teaming — \$3,000 (15.0%):**
   * Engagement of an independent third-party AI security expert to review dataset isolation, verify zero label leakage, and stress-test trajectory scenarios.
4. **Cloud Infrastructure & Open-Access Publication — \$2,000 (10.0%):**
   * CI/CD benchmarking infrastructure, OpenTelemetry test environments, and open-access publication fees.

---

### Field 9: Applicant Background & Track Record
**Principal Investigator: Creúsio Adolfo Gaspar Kizua (São Paulo, Brazil)**
* **6+ years of hands-on engineering experience** in high-throughput financial payment systems, distributed observability, and critical banking infrastructure.
* **Led technical team of 13 engineers** operating 24×7 mission-critical transaction processing environments.
* **Governed technical architecture and observability for 33 regulated banking and payment acquiring APIs**, ensuring strict compliance with Central Bank of Brazil regulations (BACEN Resolução 85/2021) and PCI-DSS v4.0.
* Advanced expertise in enterprise telemetry and distributed control: **OpenTelemetry, Kubernetes, Prometheus, Splunk, Dynatrace, and Grafana**.
* Creator of the ARKHÉ trajectory intelligence methodology, applying dynamical systems and queueing theory to defensive multi-agent AI cybersecurity.

---

### Field 10: Open Source & Reproducibility Commitment
* Fully licensed under **Apache-2.0**.
* Reviewers can clone and reproduce the functional 30-trajectory pilot locally today with 60 passing tests (`python -m unittest discover tests`, `python -m harness.agent_benchmark_runner --config configs/pilot.yaml`, `python -m evaluator.evaluate --run results/pilot`).
* All outputs feature SHA-256 deterministic hashes and machine-readable execution manifests.

---

### Field 11: Methodological Risks & Mitigations
* *Statistical Non-Significance:* Mitigated by expanding to 300 canonical trajectories across 3 repetitions (2,700 runs) with paired Wilcoxon signed-rank tests. If the hypothesis is refuted in specific scenarios, findings will be published with full scientific transparency.
* *Latency Overhead:* Mitigated by local lexical and boundary proximity calculation (<5 ms), reserving LLM inference for elevated risk zones.
* *Label Leakage:* Mitigated by Pydantic runtime schema validation and AST-based CI test suites.

---

### Field 12: OpenAI Models & Rationale
* **`gpt-4o` (snapshot `gpt-4o-2024-08-06`):** Used for complex adversarial scenario synthesis, generating diverse unseen prompt variations, and qualitative evaluation (LLM-as-a-judge).
* **`gpt-4o-mini` (snapshot `gpt-4o-mini-2024-07-18`):** Used as the primary competitive per-event semantic guardrail baseline and in the trajectory evaluator.

---

### Field 13: Relevant Project Links & Artifacts
* **GitHub Repository:** `https://github.com/creusiobd/arkhe-benchmark-lab`
* **Development Branch:** `feat/cybersecurity-grant-hardening`
* **Empirical Pilot Report ($n=30$):** `results/pilot/pilot_report.md`
* **Execution Manifest & Hashes:** `results/pilot/execution_manifest.json`
* **Research Risk Registry:** `docs/research_risks.md`
