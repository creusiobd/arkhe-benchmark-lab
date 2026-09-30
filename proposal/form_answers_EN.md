# OpenAI Cybersecurity Grant Program — Application Form Answers (English)

## 1. Project Title
**ARKHÉ: Trajectory-Oriented Boundary Defense and Pre-Violation Anticipation Benchmark for Autonomous AI Agents**

---

## 2. Executive Summary (Abstract)
Autonomous AI agents interacting with APIs, enterprise databases, and external environments present an emerging security challenge: **mission drift, indirect prompt injection propagation, and privilege escalation occur across multi-step sequences rather than in isolated prompt interactions**. Conventional perimeter controls—such as regex-based deterministic filtering or single-step LLM-as-a-judge classifiers—evaluate operations in isolation, remaining blind to cumulative behavioral changes until after a boundary breach occurs.

ARKHÉ introduces an open-source, empirical benchmark evaluating **trajectory-oriented observability** against autonomous agent boundary violations. By mapping agent execution sequences into a dynamic state space and tracking velocity, acceleration, and semantic phase drift, ARKHÉ detects unauthorized capability expansion and mission deviation **steps before execution**. 

In our hermetic pilot benchmark ($N = 65$ trajectories across development, validation, test, and a strictly disjoint blind holdout split), trajectory monitoring achieves statistically significant anticipation ($p < 0.001$, paired Wilcoxon signed-rank test) with higher overall F1 accuracy than both isolated deterministic rules and isolated single-step LLM semantic classifiers, while operating at $O(1)$ telemetry inference latency.

---

## 3. Problem Statement & Motivation
State-of-the-art LLM defense research has primarily targeted input sanitization, prompt injection guardrails, and post-execution audit logging. However, when autonomous agents execute complex multi-step workflows (e.g., tool calling, web scraping, SQL generation, and code execution), adversaries exploit compound vulnerabilities:
1. **Low-and-Slow Deviation:** The agent executes individually benign tool calls that gradually construct an unauthorized capability (e.g., directory listing $\rightarrow$ temporary file staging $\rightarrow$ external payload fetch).
2. **Context Window Contamination:** Indirect prompt injection embedded in external data alters the agent’s internal objective without triggering lexical alarms.
3. **Reactive Detection Latency:** Traditional perimeter security and single-step classifiers flag the incident only when the final unauthorized payload executes (e.g., exfiltration to an untrusted IP), providing **zero lead time for preemptive intervention**.

---

## 4. Technical Innovation & Methodology
The ARKHÉ benchmark formalizes agent behavior as an observable trajectory:
$$\mathcal{T} = \{(t_i, a_i, o_i, \mathbf{s}_i)\}_{i=1}^T$$
where each step $i$ contains action $a_i$, tool observation $o_i$, and an observable state vector $\mathbf{s}_i$.

ARKHÉ evaluates three distinct defense paradigms under identical, blind conditions:
1. **Deterministic-Event-Rule-Baseline:** Static policy matching (regex, blocklists) on individual action payloads.
2. **Semantic-Event-Classifier-Baseline:** An isolated LLM-as-a-judge (utilizing OpenAI API `gpt-4o-mini` with structured Pydantic schema `SemanticClassificationResponse` or deterministic offline proxy) that classifies each step independently without state history.
3. **ARKHÉ-Trajectory-Sentinel:** A state-space trajectory sentinel tracking temporal momentum, state transition entropy, cumulative capability drift, and phase portrait divergence.

### Strict Anti-Leakage & Blind Evaluation
- **Zero Label Leakage:** Observation inputs are stripped of ground truth metadata, and trajectory IDs are cryptographically hashed to opaque 16-character hex strings (`traj_<sha256[:16]>`), preventing heuristic split recognition.
- **Disjoint Blind Holdout:** The holdout split uses completely disjoint injection payloads and target tools unobserved in development or validation.
- **Statistical Rigor:** All proportions include Wilson score 95% confidence intervals, lead-time shifts are tested with paired Wilcoxon signed-rank tests, and paired detector discordance is evaluated with exact two-tailed McNemar tests.

---

## 5. OpenAI API Integration & Alignment
ARKHÉ provides first-class native integration with the OpenAI API via `OpenAISemanticClient`:
- Utilizes `openai>=1.30.0` structured outputs (`client.beta.chat.completions.parse`) targeting Pydantic models.
- Implements exponential backoff retry for rate limit (`RateLimitError`) and connection resiliency.
- Supports model families: `gpt-4o-mini`, `gpt-4o`, and reasoning models (`o1`, `o3-mini`).
- **Hermetic Offline Mode:** For zero-cost, privacy-preserving, and CI execution, the benchmark provides an explicit `offline_proxy` mode. No silent fallback occurs; if `mode="openai_api"` is requested without an API key, the runner fails fast.

---

## 6. Tiered Budget & Resource Request

To ensure full transparency and provide OpenAI reviewers with flexible commitment options, we structure our resource request into three tiers:

### Tier A: Core API Credits ($15,000 – $25,000 in OpenAI API Credits)
- **Scope:** Scale benchmark dataset from 65 to 5,000+ diverse agent trajectories across 15 enterprise tool environments.
- **API Utilization:** Run structured semantic evaluations across `gpt-4o-mini`, `gpt-4o`, and `o1` to benchmark trajectory-aware LLM agents against isolated step evaluators.
- **Output:** Public open-source dataset, multi-model benchmark leaderboard, and comprehensive empirical paper.

### Tier B: Comprehensive Research Grant ($25,000 API Credits + $25,000 Research Stipend = $50,000 Total)
- **Scope:** Complete Tier A, plus:
  1. **Adversarial Red-Teaming Campaign:** Commission human security researchers and red teams to generate novel adaptive prompt injection and agent jailbreak trajectories.
  2. **Multi-Agent Boundary Defense:** Extend benchmark to collaborative multi-agent swarms (e.g., supervisor-worker topologies) where compromise propagates across agent communications.
  3. **Real-Time Intervention SDK:** Develop open-source middleware providing real-time pre-execution halting for LangChain, AutoGen, and OpenAI Assistants API.
- **Budget Allocation:**
  - $25,000: OpenAI API Credits for synthetic generation, semantic classification baselines, and multi-turn red-teaming.
  - $18,000: Security researcher and red-team stipends for novel attack trajectory authoring.
  - $7,000: Reproducible cloud compute, benchmarking infrastructure, and publication dissemination.

### Tier C: Focused API Grant ($10,000 in OpenAI API Credits)
- **Scope:** Calibrate baseline performance across 1,000 trajectories on `gpt-4o` and `gpt-4o-mini`, validating statistical equivalence and latency trade-offs between trajectory sentinels and frontier LLM evaluators.

---

## 7. Open Source & Community Deliverables
1. **Permissive Open Source:** Codebase under MIT / Apache-2.0, datasets under CC-BY-4.0.
2. **Reproducibility Guarantee:** 1-click reproduction scripts (`reproduce_grant_pilot.sh` and `.ps1`) and continuous CI verification on GitHub Actions.
3. **Dataset Governance:** Machine-readable dataset cards following Hugging Face and Gebru et al. standards.
4. **Responsible Disclosure:** Formal vulnerability reporting guidelines (`SECURITY.md`) and dual-use mitigation policies (`docs/responsible_disclosure.md`).

---

## 8. Research Limitations & Scientific Honesty
- **Synthetic Step Grounding:** Current pilot trajectories use synthetic execution traces modeled on real CVEs and OWASP Top 10 for LLMs; future phases will capture live containerized sandboxes.
- **Deterministic Proxy Equivalence:** The `offline_proxy` approximates frontier model semantic judgments for testing; live API evaluations will measure real-world prompt variance and cost implications.
- **No Absolute Guarantees:** We explicitly avoid claims of "100% security", "zero false positives", or "infallible defense". All claims in ARKHÉ are delimited by bounded empirical confidence intervals and paired statistical hypothesis tests.
