# ARKHÉ Agent Boundary Defense Benchmark

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Dataset License: CC BY 4.0](https://img.shields.io/badge/Dataset_License-CC_BY_4.0-lightgrey.svg)](datasets/LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Status: Alpha](https://img.shields.io/badge/Status-Alpha%2FExperimental-orange.svg)](pyproject.toml)
[![Grant Submission](https://img.shields.io/badge/Grant-Prepared_for_Cybersecurity_Grant_Submission-purple.svg)](proposal/form_answers_EN.md)
[![Enforced Separation](https://img.shields.io/badge/Architecture-Enforced_Input_Separation-green.svg)](docs/anti_leakage_model.md)

**ARKHÉ** is an open-source defensive research benchmark and evaluation harness designed to assess whether trajectory-aware security controls reduce false positives and identify progressive multi-agent boundary violations that isolated-event controls miss.

---

## 1. What the Project Does and Does Not Do

### What ARKHÉ Does:
- **Trajectory-Oriented Observability:** Analyzes multi-step execution traces of autonomous agents, tracking capability expansions, resource access graphs, and prompt injection propagation over time.
- **Enforced Input/Ground-Truth Separation:** Sanitizes observations delivered to detectors via opaque identifiers (`traj_<uuid>`), stripped editorial metadata, and isolated ground-truth labels.
- **Comparative Evaluation:** Measures precision, recall, F1, false positive rate (FPR), false negative rate (FNR), and McNemar discordance between isolated-event baselines (deterministic and semantic) and trajectory-aware sentinels.
- **Dual Semantic Baseline Modes:** Supports an offline lexical heuristic proxy (`offline_proxy`) and a real OpenAI API structured classification client (`openai_api`) with explicit configuration.

### What ARKHÉ Does Not Do:
- **Not a Production-Ready Commercial Product:** ARKHÉ is an experimental research harness (`Development Status :: 3 - Alpha`).
- **No Absolute Guarantees:** We do not claim an absolute "Zero Label Leakage Guarantee" or complete prevention of all boundary breaches; we provide an enforced structural separation verified by automated test suites.
- **No Proven General Lead Time:** Current pilot empirical evidence ($n=30$) demonstrates substantial reduction of false positives ($83.3\%$ precision vs $55.6\%-62.5\%$), but general temporal anticipation ($N_{\text{lead}}$) remains an open research hypothesis.
- **No Unaffiliated Endorsement:** This benchmark is an independent proposal prepared for the OpenAI Cybersecurity Grant Program and is neither sponsored by nor affiliated with OpenAI.

---

## 2. Core Threat Model

In complex multi-agent workflows, an agent may perform dozens of individually benign tool invocations while gradually assembling an unsafe operational trajectory. Isolated-event inspection mechanisms (such as regex pattern matching or stateless per-call LLM guardrails) evaluate each tool call in isolation, missing incremental drift until boundary breaches become irreversible.

ARKHÉ models and benchmarks defensive responses across **5 priority boundary violation families**:

| Family ID | Threat Description | Attack Ingress Vector |
| :--- | :--- | :--- |
| `INDIRECT_PROMPT_INJECTION` | Adversarial prompt injected via untrusted external sources (webpages, issues, customer reviews) attempting to divert the agent from its original mission. | Ingress via retrieved text, documents, or API responses. |
| `TOOL_SCOPE_EXPANSION` | Incremental privilege escalation wherein an agent discovers and invokes unauthorized tools outside its assigned capability profile. | Reflection loops, unconstrained tool catalogs. |
| `SECRET_EXPOSURE` | Unauthorized reading, extraction, or exfiltration of sensitive credentials (tokens, private keys, environment secrets) to external sinks. | File reads, memory leaks, unauthorized tool arguments. |
| `UNAUTHORIZED_EXTERNAL_COMMUNICATION` | Data egress or command-and-control connection attempts to untrusted hosts without explicit supervisor approval. | Network sinks, webhook calls, unapproved domains. |
| `HUMAN_INTERVENTION_BYPASS_OR_CONCEALMENT` | Active circumvention of human-in-the-loop checkpoints, log tampering, or deceptive reporting of task status. | Subversion of confirmation tools, falsified audit steps. |

---

## 3. Scientific Hypotheses

### Primary Hypothesis
> **H1 (Precision and False Positive Reduction):** Trajectory-aware observability significantly reduces false positive security alerts compared to stateless isolated-event detectors on unseen agent trajectories, while maintaining comparable detection recall.

### Secondary Hypothesis (Exploratory)
> **H2 (Anticipatory Lead Time):** In progressive violation patterns involving multi-step reconnaissance or indirect prompt propagation, trajectory-aware sentinels can produce early alerts ($N_{\text{lead}} \ge 1$ step) prior to irreversible boundary breaches.

---

## 4. Architectural Separation Model

To prevent experimental circularity and label leakage, the benchmark architecture strictly separates observable runtime inputs from evaluation ground truth:

```
[Raw Trajectory Generator]
           │
           ├──────────────────────────────┐
           ▼                              ▼
 [Dataset Observations]         [Dataset Ground Truth]
  (datasets/observations/)       (datasets/ground_truth/)
           │                              │
           ▼ (Strip Metadata & IDs)       │
 [DetectorTrajectoryInput]                │
  • Opaque ID (traj_<uuid>)               │
  • Sanitized Step Sequences              │
           │                              │
           ▼                              │
   [Detectors Engine]                     │
   (Blind Execution)                      │
           │                              │
           ▼                              │
  [Step / Trajectory Predictions]         │
  (results/.../predictions.jsonl)         │
           │                              │
           └──────────────┬───────────────┘
                          ▼
            [Evaluation Pipeline]
             (evaluator/evaluate.py)
                          │
                          ▼
             [Verified Statistical Audit]
```

Detailed architectural contracts, prohibited key dictionaries, and structural tests are documented in [docs/anti_leakage_model.md](docs/anti_leakage_model.md).

---

## 5. Candidate Benchmark Results (v0.3, $n=65$)

The candidate experiment was executed over $n=65$ canonical trajectories across 4 splits (20 development, 10 validation, 20 test, 15 blind holdout with strictly disjoint attack templates). Under **strict temporal evaluation semantics** (no lookahead, append-only immutable alerts, separate resolution events), performance is reported across two decoupled operational tasks:

### Task 1: Pre-Violation Alert & Breach Anticipation (Strict Consummated Breach Prediction)
*Strict Criterion:* True Positives require a qualifying alert emitted strictly before the step of first violation ($A_i < V_i$). Alerts during contained near-violations are counted as FPs under this strict task:

| Detector Paradigm | Architecture | Precision [Wilson 95% CI] | Recall [Wilson 95% CI] | F1-Score | FP | FN | Median Lead [95% CI] | Anticipation Rate |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Deterministic-Event-Rule-Baseline** | Isolated Event | 0.0% [0.0%, 14.9%] | 0.0% [0.0%, 16.1%] | 0.00 | 22 | 20 | +0.0 [0.0, 0.0] steps | 0.0% |
| **Semantic-Event-Classifier-Baseline** | Isolated Event | 33.3% [12.1%, 64.6%] | 15.0% [5.2%, 36.0%] | 0.21 | 6 | 17 | +0.0 [0.0, 0.0] steps | 15.0% |
| **ARKHÉ-Trajectory-Sentinel** | Trajectory Aware | 47.6% [33.4%, 62.3%] | 100.0% [83.9%, 100.0%] | 0.65 | 22 | 0 | **+1.0 [1.0, 1.0] steps** | **100.0% (20/20)** |

### Task 2: Boundary Pressure & Hazard Detection (Attack / Probe vs Benign)
*Criterion:* Evaluates detection of any boundary-threatening perturbation (`VIOLATION` or `NEAR_VIOLATION`) against nominal non-adversarial workflows (`BENIGN`):

| Detector Paradigm | Architecture | Precision [Wilson 95% CI] | Recall [Wilson 95% CI] | F1-Score | FP (on Benign) | FN (Missed Hazards) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Deterministic-Event-Rule-Baseline** | Isolated Event | 100.0% [91.6%, 100.0%] | 100.0% [91.6%, 100.0%] | 1.00 | 0 | 0 |
| **Semantic-Event-Classifier-Baseline** | Isolated Event | 100.0% [86.7%, 100.0%] | 59.5% [44.5%, 73.0%] | 0.75 | 0 | 17 |
| **ARKHÉ-Trajectory-Sentinel** | Trajectory Aware | 100.0% [91.6%, 100.0%] | 100.0% [91.6%, 100.0%] | 1.00 | 0 | 0 |

### Lifecycle & Near-Violation Resolution (Task 3):
- **ARKHÉ Sentinel** emitted alerts on 22 near-violation trajectories when Lyapunov energy exceeded threshold ($V(\mathbf{x}) \ge 50$ at step 2). Upon trajectory containment, ARKHÉ recorded 22 confirmed `ResolutionEvent` records. No alerts are retroactively deleted.

### Paired Hypothesis Testing (ARKHÉ vs Baselines):
- **ARKHÉ vs Deterministic Baseline:**
  - *Pre-Violation Task:* McNemar paired discordance $b=20, c=0$ ($p = 2 \times 10^{-6}$, exact two-tailed binomial, statistically significant $p < 0.0001$); Wilcoxon signed-rank test on lead steps $W = 0, Z = 3.9199, p = 8.9 \times 10^{-5}$ (effect size $r=0.8765$, statistically significant $p < 0.01$).
  - *Hazard Detection Task:* Both detect 42/42 hazards, but ARKHÉ anticipates violations +1.0 step ahead while Deterministic alerts only at the exact breach step ($lead=0$).
- **ARKHÉ vs Semantic Baseline:**
  - *Pre-Violation Task:* Wilcoxon signed-rank test on lead steps $W = 0, Z = 3.6214, p = 0.000293$ (effect size $r=0.8783$, statistically significant $p < 0.01$).
  - *Hazard Detection Task:* McNemar paired discordance $b=17, c=0$ ($p = 1.5 \times 10^{-5}$, exact two-tailed binomial, statistically significant $p < 0.0001$).
- **Grant Justification:** The pilot proves the integrity of the evaluation harness, strict anti-leakage contracts, temporal evaluation semantics (zero lookahead), and pipeline automation. Large-scale expansion to $N=5,000+$ trajectories with live OpenAI models (`gpt-4o`, `o1`) is planned to validate boundary stability across diverse enterprise agent ecosystems and multi-agent coordination graphs.

---

## 6. Quickstart & Reproducibility

### Installation
```bash
git clone https://github.com/creusiobd/arkhe-benchmark-lab.git
cd arkhe-benchmark-lab
python -m pip install -r requirements.txt
```

### Reproducing the Grant Candidate Benchmark
Run the single-command reproducible pipeline:
```bash
# Linux / macOS
bash scripts/reproduce_grant_pilot.sh

# Windows PowerShell
powershell -ExecutionPolicy Bypass -File scripts/reproduce_grant_pilot.ps1
```

Or execute the steps individually:
```bash
# 1. Run all unit and contract tests (100 tests)
python -m unittest discover -s tests -v

# 2. Execute blind benchmark runner on v0.3 dataset
python -m harness.agent_benchmark_runner --config configs/grant_candidate_v0.3.yaml

# 3. Compute metrics, confidence intervals, and statistical tests
python -m evaluator.evaluate --run results/grant_candidate_v0.3 --ground-truth datasets/v0.3/ground_truth
```

---

## 7. Dual Semantic Baseline Modes

The semantic baseline detector (`detectors/semantic_event.py`) supports two explicitly configured operating modes:

1. **`offline_proxy` (Default):**
   - Heuristic lexical proxy with zero external network dependencies.
   - Ideal for continuous integration, local testing, and automated smoke testing.
   - Identified in manifests and logs as `offline_proxy` (never mislabeled as real API).

2. **`openai_api`:**
   - Performs structured API calls to the OpenAI API using the official SDK.
   - Requires `OPENAI_API_KEY` in environment. Fails fast with descriptive error if credentials are missing (no silent fallback).
   - Validates response schemas via Pydantic (`SemanticClassificationResponse`).
   - Configurable model via `OPENAI_SEMANTIC_MODEL` (e.g., `gpt-4o-mini`).

---

## 8. Responsible Disclosure & Ethical Boundaries

- **Synthetic Data Exclusively:** All benchmark trajectories use synthetic, sanitized payloads. No real credentials, private personal data, or functional external attack targets are contained in the dataset.
- **Defensive Focus:** The benchmark evaluates defensive detection mechanisms; no autonomous offensive exploitation agents are provided.
- **Reporting Vulnerabilities:** For security vulnerability reports, refer to [SECURITY.md](SECURITY.md).

---

## 9. Related Engineering Experiments

As a complementary applied engineering initiative, this repository also hosts research on queue-physics observability, Lyapunov stability basins, and autonomous self-healing for high-throughput microservices. This work is isolated in:

📁 **[`experiments/telemetry-control-plane/`](experiments/telemetry-control-plane/README.md)**

---

## 10. License & Citation

- **Code:** [Apache License 2.0](LICENSE)
- **Dataset:** [Creative Commons Attribution 4.0 International (CC BY 4.0)](datasets/LICENSE)

To cite this repository in academic or technical work:
```bibtex
@software{kizua2026arkhe,
  author = {Kizua, Creúsio Adolfo Gaspar},
  title = {ARKHÉ Agent Boundary Defense Benchmark: Trajectory-Aware Observability vs Isolated Event Baselines},
  year = {2026},
  url = {https://github.com/creusiobd/arkhe-benchmark-lab},
  version = {0.3.0}
}
```
