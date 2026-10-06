# Contributing to ARKHÉ Agent Benchmark

Thank you for your interest in contributing to the ARKHÉ Agent Boundary Defense Benchmark. We welcome defensive contributions, dataset extensions, and detector baselines from researchers and practitioners.

## Core Defensive Principles

1. **Enforced Observation/Label Separation:**
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

## Independent SDK contributions

Build and validate the SDKs independently: `python -m pytest tests/defense tests/trajectory tests/audit -q`, `python sdk/build.py`, `python trajectory-sdk/build.py`. CI defines Windows/Linux with Python3.10–3.12; local evidence is Python3.12, and remote CI remains to be executed.

Keep defensive agent evaluation separate from operational/card journeys. For changes to authority, tenant isolation, timing or recovery, include a meaningful synthetic reproduction. Treat labels as evaluator data, not SDK input. Preserve baseline policies and configuration bindings during replay. The first external pilot is prospective; ARKHÉ is currently an independent initiative led by Creúsio, with no partner claimed.
