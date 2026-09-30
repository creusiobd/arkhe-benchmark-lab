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

## 5. Preliminary Pilot Results ($n=30$)

The pilot experiment was executed over $n=30$ canonical trajectories (12 development, 6 validation, 12 test) evaluated across three baseline paradigms:

| Detector Paradigm | Architecture | Precision [Wilson 95% CI] | Recall [Wilson 95% CI] | F1-Score | False Positives | Median Lead ($N_{\text{lead}}$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Deterministic-Event-Rule-Baseline** | Isolated Event | 62.5% [38.6%, 81.5%] | 100.0% [72.2%, 100.0%] | 0.77 | 6 | +0.0 steps |
| **Semantic-Event-Classifier-Baseline** | Isolated Event | 55.6% [33.7%, 75.4%] | 100.0% [72.2%, 100.0%] | 0.71 | 8 | +1.0 steps |
| **ARKHÉ-Trajectory-Sentinel** | Trajectory Aware | **83.3% [55.2%, 95.3%]** | **100.0% [72.2%, 100.0%]** | **0.91** | **2** | **+0.0 steps** |

*All statistics are computed directly by `evaluator/evaluate.py` from raw predictions. Artifacts are archived in `results/pilot/`.*

---

## 6. Quickstart & Reproducibility

### Installation
```bash
git clone https://github.com/creusiobd/arkhe-benchmark-lab.git
cd arkhe-benchmark-lab
python -m pip install -r requirements.txt
```

### Reproducing the Benchmark
Run the single-command reproducible pipeline:
```bash
# Linux / macOS
bash scripts/reproduce_grant_pilot.sh

# Windows PowerShell
.\scripts\reproduce_grant_pilot.ps1
```

Or execute the steps individually:
```bash
# 1. Run all unit and contract tests
python -m unittest discover -s tests -v

# 2. Execute blind benchmark runner
python -m harness.agent_benchmark_runner --config configs/pilot.yaml

# 3. Compute metrics, confidence intervals, and statistical tests
python -m evaluator.evaluate --run results/pilot
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
