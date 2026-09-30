# Contributing to ARKHÉ Agent Benchmark

Thank you for your interest in contributing to the ARKHÉ Agent Boundary Defense Benchmark. We welcome defensive contributions, dataset extensions, and detector baselines from researchers and practitioners.

## Core Defensive Principles

1. **Zero Label Leakage Guarantee:**
   - Detectors must strictly consume `StepObservation` objects.
   - Detectors must **never** import or consume `contracts.ground_truth` or precalculated risk/drift scores.
   - Automated tests (`tests/test_no_label_leakage.py` and `tests/test_contract_separation.py`) will automatically fail any PR violating this separation.

2. **Synthetic Data Only:**
   - Any added trajectory or template must use fake credentials (`ARKHE_FAKE_TOKEN_DO_NOT_USE_*`) and mock sinks (`localhost`, `.test`, or `.internal`).

3. **Statistical Rigor:**
   - Benchmark additions must report confidence intervals (Wilson score 95% CI for binomial proportions, Bootstrap for median lead time).
   - Never report ungrounded point estimates.

## Contribution Workflow

1. **Fork and Branch:**
   ```bash
   git checkout -b feat/your-contribution
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Verification & Tests:**
   ```bash
   python -m unittest discover tests -v
   ```

4. **Verify Grant Candidate v0.3 Reproduction:**
   ```bash
   # On POSIX / Linux / macOS:
   bash scripts/reproduce_grant_pilot.sh

   # On Windows PowerShell:
   powershell -ExecutionPolicy Bypass -File scripts/reproduce_grant_pilot.ps1
   ```

5. **Submit a Pull Request:**
   - Explain the defensive contribution.
   - Include test logs and ensure all anti-leakage checks pass.
   - Target the `feat/*` branch or open a draft PR against `main`. Do not push directly to `main`.
