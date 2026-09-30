# Official Application Form Answers — OpenAI Cybersecurity Grant Program

This document contains the consolidated, audit-grade answers for each field of the **OpenAI Cybersecurity Grant Program** application form, in English, aligned with version **v0.3** of the ARKHÉ Agent Boundary Defense Benchmark.

---

### Field 1: Project Title
**ARKHÉ Agent Boundary Defense Benchmark: Empirical Evaluation of Trajectory-Aware Observability Against Boundary Violations in AI Agent Systems**

---

### Field 2: One-line Description
An open-source defensive benchmark evaluating whether trajectory-oriented state-space observability detects mission drift, indirect prompt injection propagation, and boundary violations in autonomous AI agents prior to isolated atomic event guardrails.

---

### Field 3: Problem Statement
*(Strict constraint: $\le 200$ words)*

Autonomous AI agents executing enterprise workflows chain dozens of tool invocations, context retrievals, and external communications. In these multi-step pipelines, individual actions often appear benign and policy-compliant when evaluated in isolation. However, across sequential steps, these operations compound into high-risk behavioral trajectories.

Existing defensive perimeter controls—such as single-call guardrails, atomic semantic classifiers, and static regex blocklists—suffer from temporal blindness. They evaluate the immediate tool invocation without contextual memory, remaining blind to silent mission drift, cumulative context contamination from indirect prompt injection, and progressive boundary encroachment.

This point-in-time paradigm creates a structural vulnerability: agents undergo intent hijacking and stealthy privilege escalation, only triggering alarms when exfiltration or irreversible system compromise is already executing. The critical gap is the absence of an open, reproducible scientific benchmark measuring whether trajectory-oriented state-space observability can anticipate boundary violations with positive lead time ($N_{\text{lead}} > 0$) and reduced false positives compared to isolated-event defenses.

*(Word count: 143 words — Approved under the 200-word limit)*

---

### Field 4: Research Hypothesis & Methodology
**Central Hypothesis:** Distributed weak signals across an agent's execution sequence—context contamination, semantic divergence between active intent and declared mission, unprompted capability expansion, and boundary approach velocity—enable identification of security deviations at least 1 to 2 steps before an explicit violation executes ($N_{\text{lead}} \ge 1$), while maintaining false positive rates strictly lower than isolated semantic guardrails.

**Experimental Design & Strict Anti-Leakage Separation:**
To eliminate experimental circularity and label leakage, the benchmark enforces two strictly isolated architectural layers:
1. *Observable Layer (`DetectorTrajectoryInput`):* Delivered to detectors in real time, containing only an opaque identifier (`traj_<sha256[:16]>`), declared mission, sanitized action, available capabilities, permissible boundaries, and raw tool outputs. Ground truth labels, breach step indices, and precalculated scores are strictly prohibited and enforced recursively via Pydantic validators and AST import guards.
2. *Reserved Ground Truth (`TrajectoryGroundTruth`):* Sealed separately for exclusive use by the independent evaluator, containing the true class, breach step index, and causal justification.
3. *Strictly Disjoint Blind Holdout Split:* The v0.3 dataset incorporates 15 trajectories in a blind split with attack templates 100% disjoint from development and validation sets (verified 0% lexical Jaccard overlap).

**Mathematical Formalization & State Space:**
ARKHÉ models execution dynamics using a continuous subword embedding kernel ($\mathbb{R}^{64}$) and a quadratic Lyapunov candidate energy function:
$$V(\mathbf{x}_t) = \mathbf{x}_t^T \mathbf{P} \mathbf{x}_t > 0 \quad (\mathbf{P} \succ 0)$$
tracking state vector $\mathbf{x}_t = [d_m(t), c_p(t), b_p(t), \dot{b}_p(t), \mathcal{H}_s(t), \mu_c(t)]^T$, where cross-coupling between mission divergence ($d_m$) and context contamination ($c_p$) detects pre-violation instability steps before forbidden tool calls occur.

**Scale and Statistical Treatment:**
Evaluated across $n = 65$ canonical trajectories across 5 threat families (development: 20, validation: 10, test: 20, blind holdout: 15). The evaluation engine computes Wilson score 95% confidence intervals, bootstrap confidence intervals for median lead time, paired Wilcoxon signed-rank tests for anticipation lead steps, and exact two-tailed McNemar tests for paired detector discordance.

---

### Field 5: Deliverables & Expected Outcomes
1. **Canonical Open Dataset (v0.3 and Large-Scale Expansion):** Standardized JSONL format across 5 threat families, licensed under CC-BY-4.0, archived with permanent DOIs on Zenodo and HuggingFace.
2. **Open Source Benchmark Harness & Evaluator (Apache-2.0):** Modular Python codebase with deep anti-leakage contracts, multi-backend execution (native OpenAI API and hermetic offline proxy), and automated statistical reporting.
3. **Three Auditable Reference Detectors:** Deterministic rule baseline, single-step semantic classifier (integrating `OpenAISemanticClient` with Pydantic structured outputs `SemanticClassificationResponse` or deterministic proxy), and *ARKHÉ Trajectory Sentinel*.
4. **Empirical Paper & Open Technical Report:** Comprehensive methodology, mathematical proof of Lyapunov boundary stability, and paired significance analysis.
5. **1-Click Reproducibility Pipeline:** Automated reproduction scripts (`scripts/reproduce_grant_pilot.sh` and `.ps1`) and continuous GitHub Actions CI (`grant-benchmark.yml`).

---

### Field 6: Defensive Orientation & Safety
The project is strictly defensive in purpose, architecture, and deployment:
* **Exclusively Synthetic & Sanitized Data:** All scenarios utilize identifiable mock credentials (`ARKHE_FAKE_TOKEN_DO_NOT_USE_*`) and local network sinks (`http://localhost:8080/mock-sink`), completely decoupled from production infrastructure.
* **No Functional Exploits:** Scenarios evaluate behavioral divergence at the telemetry and observation layer without distributing exploitable attack code or weaponized payloads.
* **Defensive Utility:** Equips security engineers, agent framework authors (LangChain, AutoGen, CrewAI), and frontier lab safety teams with empirical evidence on pre-violation lead times and false positive trade-offs to harden agent runtimes against prompt injection propagation.

---

### Field 7: Work Plan & Timeline (6 Months)
* **Month 1 (M1 — Dataset Scaling & Formalization):** Expand canonical dataset to 1,000+ multi-step trajectories across 15 enterprise tool environments with automated anti-leakage AST audits.
* **Month 2 (M2 — Baseline Hardening & API Integration):** Calibrate semantic baselines across OpenAI model families (`gpt-4o`, `gpt-4o-mini`, `o1`) with structured output schemas.
* **Month 3 (M3 — Trajectory Sentinel Optimization):** Calibrate and freeze Lyapunov matrix parameters and continuous embedding projection across development and validation sets.
* **Month 4 (M4 — Large-Scale Blind Execution):** Execute large-scale blind benchmark evaluations ($N = 5,000+$ runs); process full statistical suites (Wilson 95%, Wilcoxon, McNemar).
* **Month 5 (M5 — Independent Red-Teaming Campaign):** Commission independent external security researchers to challenge benchmark generalization with novel adaptive prompt injections.
* **Month 6 (M6 — Open Source Release & Dissemination):** Deposit datasets to Zenodo/HuggingFace, release public Apache-2.0 repository, and publish technical preprint.

---

### Field 8: Tiered Budget & Justification (3 Tiers)

To provide the OpenAI evaluation committee with maximum flexibility, the resource request is structured into three modular tiers:

#### Tier A: Core API Credits ($15,000 – $25,000 in OpenAI API Credits)
* **Focus:** Large-scale experimental evaluation against frontier models (`gpt-4o`, `gpt-4o-mini`, `o1`).
* **Credit Utilization:** Execute 5,000+ agent trajectories with step-by-step structured semantic evaluations, prompt variance robustness testing, and LLM-as-a-judge calibration.
* **Direct Cash Cost:** $0 (zero monetary disbursement, inference credits only).

#### Tier B: Comprehensive Project with Research Stipend ($25,000 API Credits + $25,000 Research Resources = $50,000 Total)
* **OpenAI API Credits — $25,000 (50%):**
  * Synthetic trajectory generation, structured semantic baseline inference with `gpt-4o` and reasoning models (`o1`) across multi-agent workflows.
* **Principal Researcher & Engineering Stipend — $15,000 (30%):**
  * Dedicated technical effort over 6 months covering telemetry library development, formal contracts, Lyapunov kernel engineering, and statistical analysis.
* **External Security Audit & Adversarial Red-Teaming — $6,000 (12%):**
  * Bounties and contracts for independent security researchers to author novel, adaptive attack trajectories.
* **Cloud Infrastructure & Open-Access Publication — $4,000 (8%):**
  * Isolated cloud sandbox execution environments, reproducible CI/CD runners, and open-access scientific publication fees.

#### Tier C: Focused API Grant ($10,000 in OpenAI API Credits)
* **Focus:** Calibrate baseline performance across 1,000 trajectories using `gpt-4o-mini` and `gpt-4o`, quantifying latency-accuracy trade-offs between trajectory sentinels and isolated LLM evaluators.

---

### Field 9: Applicant Background & Execution Capacity
**Principal Researcher: Creúsio Adolfo Gaspar Kizua (São Paulo, Brazil)**
* **6+ years of practical engineering experience** in high-availability financial systems, mission-critical infrastructure, and large-scale distributed observability.
* **Technical Lead of an engineering team of 13 engineers** operating 24×7 banking and transactional production environments.
* **Technical governance and observability across 33 regulated APIs**, in strict compliance with cybersecurity regulatory frameworks (Central Bank of Brazil BACEN Resolution 85/2021 and PCI-DSS v4.0).
* Deep mastery of telemetry and distributed control architectures: OpenTelemetry, Kubernetes, Prometheus, Splunk, Dynatrace, and Grafana.
* Creator of the trajectory-aware agent boundary defense methodology, bridging dynamical systems stability (Lyapunov methods) with autonomous AI agent cybersecurity.

---

### Field 10: Open Source Commitment & Reproducibility
* The project is 100% open source under permissive licenses: **Apache-2.0** for codebase, **CC-BY-4.0** for datasets.
* The test suite features **112 automated tests** passing (`111 passed, 1 live test skipped`), a 1-click reproduction pipeline (`scripts/reproduce_grant_pilot.sh` and `reproduce_grant_pilot.ps1`), and continuous GitHub Actions CI (`.github/workflows/grant-benchmark.yml`).
* All evaluation artifacts are backed by cryptographically verifiable SHA-256 execution manifests, Wilson score confidence intervals, and raw predictions archived in `results/grant_candidate_v0.3/`.
