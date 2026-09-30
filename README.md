# ARKHÉ Research & Benchmark Lab

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![OpenAI Cybersecurity Grant Candidate](https://img.shields.io/badge/Candidate-OpenAI_Cybersecurity_Grant-purple.svg)](proposal/ARKHE_CYBERSECURITY_GRANT_v0.2_PT.md)
[![Zero Label Leakage](https://img.shields.io/badge/Tests-Anti--Leakage_Passing-green.svg)](tests/)

**ARKHÉ** comprises two interconnected applied defensive research initiatives:
1. **[Part I: ARKHÉ Agent Boundary Defense Benchmark](#part-i-arkhe-agent-boundary-defense-benchmark):** An open-source benchmark measuring whether trajectory-aware observability detects multi-agent boundary violations, indirect prompt injection propagation, and mission drift before isolated-event security guardrails.
2. **[Part II: ARKHÉ Telemetry & Shadow Control Plane](#part-ii-arkhe-telemetry--shadow-control-plane-apm-lab):** An OpenTelemetry-native queue-physics APM engine validating early structural saturation warning and autonomous closed-loop mitigation in high-throughput payment systems.

---

## Part I: ARKHÉ Agent Boundary Defense Benchmark

### 1. Research Core & Threat Model
In autonomous multi-agent environments, an agent may perform dozens of individually benign tool actions while progressively building an unsafe execution trajectory. Traditional isolated event filters (e.g., regex pattern matching, per-call LLM guardrails) evaluate each tool call out of context and miss incremental drift until irreversible boundary breaches occur.

ARKHÉ evaluates defensive systems across **5 critical boundary violation families**:
1. `TOOL_SCOPE_EXPANSION`: Incremental capability escalation via reflection and tool discovery.
2. `INDIRECT_PROMPT_INJECTION`: Ingress of adversarial instructions via external content (PDFs, issues, APIs).
3. `SECRET_EXPOSURE`: Cross-tenant exfiltration of credentials to mock endpoints.
4. `UNAUTHORIZED_EXTERNAL_COMMUNICATION`: Egress to unauthorized domains without supervisor consent.
5. `HUMAN_INTERVENTION_BYPASS_OR_CONCEALMENT`: Suppressing supervisor halts or doctoring audit logs.

### 2. Methodological Guarantee: Zero Label Leakage
To prevent experimental circularity and label leakage, the benchmark enforces a strict architectural separation:
* **Observable Runtime Contract (`contracts.observation.StepObservation`):** Contains strictly observable runtime signals (agent identity, current instruction, tool invocation, capability constraints, boundary policy, raw tool outputs). It strictly forbids and rejects precomputed risk scores, contamination flags, or ground truth labels.
* **Evaluation Ground Truth (`contracts.ground_truth.TrajectoryGroundTruth`):** Stored in separate files, accessible exclusively by the evaluation harness.
* **Prediction Contract (`contracts.prediction.StepPrediction`, `TrajectoryPrediction`):** Output generated dynamically by detectors during blind execution.

### 3. Empirical Pilot Results ($n=30$ Canonical Trajectories)

Evaluating on 30 rigorously balanced synthetic trajectories across the 5 attack families:

| Detector Paradigm | Precision [Wilson 95% CI] | Recall [Wilson 95% CI] | F1-Score | FP Count | Median Lead Time ($N_{\text{lead}}$) | Mean Lead Time |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Deterministic Event Rule Baseline** | 62.5% [38.6%, 81.5%] | 100.0% [72.2%, 100.0%] | 0.77 | 6 | 0.0 steps | 0.0 steps |
| **Semantic Event Classifier Baseline** | 55.6% [33.7%, 75.4%] | 100.0% [72.2%, 100.0%] | 0.71 | 8 | 1.0 steps | 0.9 steps |
| **ARKHÉ Trajectory Sentinel** | **83.3% [55.2%, 95.3%]** | **100.0% [72.2%, 100.0%]** | **0.91** | **2** | **0.0 steps** | **0.8 steps** |

*Note: For trajectories featuring prompt injection propagation, ARKHÉ achieves up to $+2$ steps of anticipatory lead time. Small-sample asymptotic Wilcoxon test noted insufficient non-zero pairs ($<5$), establishing the requirement for the full 300-trajectory grant benchmark.*

### 4. Reproducing the Benchmark Pilot

Clone repository and install dependencies:
```bash
git clone https://github.com/creusiobd/arkhe-benchmark-lab.git
cd arkhe-benchmark-lab
pip install -r requirements.txt
```

Run automated verification and pilot reproduction:
```bash
# 1. Execute all unit tests and anti-leakage audits
python -m unittest discover tests

# 2. Run blind benchmark harness across 30 trajectories
python -m harness.agent_benchmark_runner --config configs/pilot.yaml

# 3. Compute metrics, Wilson confidence intervals, and generate pilot report
python -m evaluator.evaluate --run results/pilot

# Windows 1-Click Reproduction:
.\reproduce_pilot.ps1
```

Generated audit artifacts are saved in `results/pilot/`:
- `predictions.jsonl`: Raw detector outputs per trajectory.
- `execution_manifest.json`: Execution metadata and dataset SHA-256 hashes.
- `metrics.json`: Accuracy, precision, recall, lead times.
- `confidence_intervals.json`: Wilson 95% CIs and bootstrap intervals.
- `confusion_matrices.json`: TP, FP, TN, FN breakdown.
- `pilot_report.md`: Formal markdown evaluation report.

---

## Part II: ARKHÉ Telemetry & Shadow Control Plane (APM Lab)

### 1. Queue Physics & Dynamical Systems Modeling
The telemetry lab models service degradation using **Little's Law** ($L = \lambda W$) and $M/M/c$ queuing theory rather than stochastic noise:
* **Nominal Pool:** 30 concurrent connection slots, $\lambda = 80\text{ TPS}$, $W_s = 45\text{ ms} \implies 12\%$ pool occupancy.
* **Silent Drift ($T_{+3\text{min}}$):** Latency rises to $255\text{ ms} \implies 68\%$ occupancy with zero timeouts.
* **Critical Saturation Point ($T_{+10\text{min}}$):** Latency reaches $420\text{ ms} \implies L = 33.6 > 30$, causing immediate queue overflow and retry storms ($>170\text{ TPS}$).

### 2. ARKHÉ Structural Acceleration Vector
Traditional APMs (Datadog, Dynatrace) alert only after threshold breach ($P95 > 1500\text{ms}$). ARKHÉ tracks the second-order structural acceleration vector:
$$\vec{S}_{\text{ARKHÉ}} = \left( \frac{d}{dt}\rho_{\text{pool}}, \quad \frac{W_q}{W_s}, \quad R_{\text{retry}} \right)$$

### 3. Interactive Proof-of-Value (PoV) Sandbox
To run the interactive simulation:
```bash
python run_interactive_pov.py
```
Or start the Docker stack:
```powershell
.\run_docker_stack.ps1
```

---

## Repository Structure

```
arkhe-benchmark-lab/
├── configs/                  # Benchmark configurations (configs/pilot.yaml)
├── contracts/                # Strict typed schemas (observation, prediction, ground_truth)
├── datasets/                 # 30-trajectory pilot dataset & templates
│   ├── observations/         # Observable JSONL files (development, validation, test)
│   ├── ground_truth/         # Ground truth labels (isolated from detectors)
│   └── templates/            # Attack family scenario catalogs
├── detectors/                # Evaluated defensive detectors
│   ├── base.py               # Abstract base detector contract
│   ├── deterministic_event.py # Baseline 1: Regex & target matching
│   ├── semantic_event.py     # Baseline 2: Per-event LLM guardrail proxy
│   └── arkhe_trajectory.py   # ARKHÉ: Trajectory-aware dynamical sentinel
├── harness/                  # Blind benchmark runner (agent_benchmark_runner.py)
├── evaluator/                # Independent evaluator & statistics (evaluate.py, statistics.py)
├── results/pilot/            # Reproducible pilot results and statistical reports
├── proposal/                 # OpenAI Cybersecurity Grant Proposal (PT & EN)
├── reports/                  # Initial audit, cost models, and peer reviews
├── tests/                    # 60 automated tests (including anti-leakage audits)
└── tools/                    # Cost estimators and dataset generators
```

---

## Citation & Licensing

Distributed under the **Apache-2.0 License**. See [LICENSE](LICENSE) for details.

If you reference or use this benchmark in academic or defensive research, please cite:
```bibtex
@misc{kizua2026arkhe,
  title={ARKHÉ Agent Boundary Defense Benchmark: Measuring Trajectory-Aware Observability Against Multi-Agent Boundary Violations},
  author={Kizua, Creúsio Adolfo Gaspar},
  year={2026},
  howpublished={\url{https://github.com/creusiobd/arkhe-benchmark-lab}}
}
```
