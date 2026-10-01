# Reproducibility Guide — ARKHÉ Agent Boundary Defense Benchmark

This guide provides exhaustive instructions for reproducing all benchmark results, statistical tests, and artifacts published in version **v0.3**.

> **Legacy guide:** These commands reproduce the v0.3 candidate pipeline only. They do not reproduce the v0.4 live pilot or the planned v0.5 leave-one-family-out study. The v0.4 test split was included in an exploratory live baseline run and is not an untouched test set. Use [`evaluation_protocol_v0.5.md`](evaluation_protocol_v0.5.md) for the proposed study.

---

## 1. System Requirements

- **Operating System:** Ubuntu 22.04+ LTS, Debian 12+, macOS 13+, or Windows 10/11 (PowerShell 5.1+ / Core).
- **Python Version:** Python 3.10, 3.11, or 3.12 (CI verified on 3.11 and 3.12).
- **Hardware Minimum:** 2 CPU cores, 4 GB RAM, 500 MB disk space. No GPU required (offline execution runs in CPU memory).
- **Network Access:** Not required for offline benchmark reproduction (`mode: offline_proxy`). Only required if executing live OpenAI API baseline calls.

---

## 2. Environment Setup

Clone the repository and install dependencies in an isolated virtual environment:

```bash
git clone https://github.com/creusiobd/arkhe-benchmark-lab.git
cd arkhe-benchmark-lab
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1

# Install exact dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. One-Click Reproduction

We provide automated, 1-click reproduction scripts for both Unix and Windows:

### POSIX (Linux / macOS):
```bash
bash scripts/reproduce_grant_pilot.sh
```

### Windows (PowerShell):
```powershell
powershell -ExecutionPolicy Bypass -File scripts/reproduce_grant_pilot.ps1
```

Both scripts automatically:
1. Run the current unit tests and anti-leakage contract validations.
2. Verify the v0.3 dataset (generating it deterministically if absent).
3. Run the observation-only execution harness using `configs/grant_candidate_v0.3.yaml`.
4. Run the evaluator, isolated from detectors, with the v0.3 ground truth (`datasets/v0.3/ground_truth`).
5. Validate the completeness of all output JSON/Markdown artifacts.

---

## 4. Manual Step-by-Step Reproduction

If you prefer to run each step manually:

### Step 1: Execute Full Test Suite
```bash
python -m unittest discover -s tests -v
```
*Expected Result:* The installed test suite passes. Any live OpenAI API test may require a key and incur usage; skip it unless explicitly configured.

### Step 2: (Optional) Re-generate Dataset v0.3 Deterministically
```bash
python scripts/generate_v03_dataset.py
```
*Standard Seed:* `20260930`. All trajectory observations and ground truth labels are generated identically across runs.

### Step 3: Execute Historical v0.3 Benchmark Harness
```bash
python -m harness.agent_benchmark_runner --config configs/grant_candidate_v0.3.yaml
```
*Output Directory:* `results/grant_candidate_v0.3/`
*Key File Produced:* `predictions.jsonl` and `execution_manifest.json`.

### Step 4: Run the Ground-Truth-Isolated Statistical Evaluator
```bash
python -m evaluator.evaluate \
    --run results/grant_candidate_v0.3 \
    --ground-truth datasets/v0.3/ground_truth
```
*Key Files Produced:*
- `metrics.json`: Standard classification metrics (Precision, Recall, F1, Accuracy, Lead Steps).
- `confidence_intervals.json`: Wilson score 95% CIs and Bootstrap lead step intervals.
- `confusion_matrices.json`: Exact counts for TP, FP, TN, FN across detectors.
- `hypothesis_tests.json`: Paired Wilcoxon signed-rank tests and exact two-tailed McNemar discordance tests.
- `cost_report.json`: Token consumption and latency benchmarking.
- `pilot_report.md`: Markdown summary report.

---

## 5. Live OpenAI API Evaluation (Optional)

To evaluate the historical v0.3 semantic baseline using a live OpenAI API model, use the exact model snapshot recorded in that run's configuration and manifest. Do not infer that other model IDs, including `o1`, were tested by this guide.

1. Export your API key:
   ```bash
   export OPENAI_API_KEY="sk-..."  # On Windows: $env:OPENAI_API_KEY="sk-..."
   ```

2. Edit `configs/grant_candidate_v0.3.yaml` to set `mode: "openai_api"` under `semantic_event`:
   ```yaml
   - id: "semantic_event"
     name: "Semantic-Event-Classifier-Baseline"
     class_path: "detectors.semantic_event.SemanticEventDetector"
     enabled: true
     params:
       mode: "openai_api"
       model: "gpt-4o-mini"
   ```

3. Run the live integration test to confirm connection:
   ```bash
   RUN_OPENAI_INTEGRATION=1 python -m unittest tests/test_openai_semantic_client.py
   ```

4. Run the benchmark runner and evaluator as shown in Steps 3 and 4.
