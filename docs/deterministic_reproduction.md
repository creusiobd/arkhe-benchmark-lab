# Deterministic Dataset Reproduction Guide — ARKHÉ v0.4 Hard

This document outlines the rigorous protocol for generating, verifying, and reproducing the **ARKHÉ v0.4 Hard Dataset** (`datasets/v0.4_hard/`).

---

## 1. Overview & Objective

In compliance with open scientific benchmarks and strict reproducibility standards, the ARKHÉ benchmark requires that dataset generation is **100% deterministic**:
- When executed with identical generator code, configuration, random seed, and system dependencies, the generation process produces **bitwise identical files** and exact cryptographic SHA-256 matches.
- All trajectory identifiers are derived deterministically using a one-way cryptographic hash of canonical blueprint parameters, ensuring zero trajectory ID collisions and complete opacity (preventing target leakage).
- Every dataset distribution is anchored by a machine-verifiable **Provenance Manifest** (`generation_manifest.json`) that records Git commit provenance, dirty state, configuration hash, environment details, and file-level SHA-256 checksums.

---

## 2. Canonical Trajectory ID Derivation

Trajectory identifiers do **not** use non-deterministic randomness (`uuid.uuid4()` is strictly prohibited in generation pipelines). Instead, IDs are computed deterministically via canonicalization:

### Canonical Representation Formula
$$\text{canonical} = \text{"arkhe\_v04:"} + \text{seed} + \text{":"} + \text{split} + \text{":"} + \text{template\_id} + \text{":"} + \text{gt\_class} + \text{":"} + \text{trajectory\_index}$$

$$\text{trajectory\_id} = \text{"traj\_"} + \text{SHA-256}(\text{canonical.encode('utf-8')})[:16]$$

### Properties
1. **Opacity:** The final string `traj_<16-char-hex>` conveys no human-readable information regarding split, template family, severity, or ground truth classification, preserving blinding for detectors.
2. **Deterministic Invariance:** Generating the same trajectory specification with the same seed always yields the exact same ID.
3. **Parameter Sensitivity:** Altering any parameter (e.g., changing seed from `42` to `43`, or changing class from `benign` to `boundary_pressure`) completely alters the digest.
4. **Collision Freedom:** Verified across all generated instances with zero cross-split or intra-split collisions.

---

## 3. Fast One-Click Reproduction

We provide automated verification scripts that generate the dataset twice in isolated temporary sandboxes and verify bitwise invariance across all files and manifest hashes:

### Linux / POSIX (Bash):
```bash
bash scripts/reproduce_dataset_generation.sh
```

### Windows (PowerShell):
```powershell
.\scripts\reproduce_dataset_generation.ps1
```

Both scripts invoke:
```bash
python scripts/verify_deterministic_dataset_generation.py --check-tracked
```

---

## 4. Manual Verification & Generation Protocol

### Re-generating the Tracked Dataset
To re-generate the dataset directly in `datasets/v0.4_hard/` with the canonical seed (`42`):
```bash
python scripts/generate_hard_dataset.py \
    --config configs/hard_dataset_v0.4.yaml \
    --seed 42 \
    --output-dir datasets/v0.4_hard
```

### Running the Dual-Run Verification Harness
To verify bit-for-bit reproducibility between independent sandboxes:
```bash
python scripts/verify_deterministic_dataset_generation.py --check-tracked
```

The verifier executes the following steps:
1. Creates `Run A` in a fresh temporary directory.
2. Creates `Run B` in a second temporary directory.
3. Computes SHA-256 digests for all 9 core generated files:
   - `observations/development.jsonl`
   - `observations/validation.jsonl`
   - `observations/test.jsonl`
   - `ground_truth/development_labels.jsonl`
   - `ground_truth/validation_labels.jsonl`
   - `ground_truth/test_labels.jsonl`
   - `templates/templates_catalog.json`
   - `dataset_card.md`
   - `LICENSE`
4. Compares SHA-256 digests of Run A and Run B (must be 100% bitwise identical).
5. Compares `deterministic_metadata` of `generation_manifest.json` between runs.
6. When `--check-tracked` is set, verifies that tracked repository files in `datasets/v0.4_hard/` match the generated outputs bit-for-bit.

---

## 5. Provenance Manifest (`generation_manifest.json`)

Each dataset release contains `generation_manifest.json` structured into two distinct sections:

```json
{
  "manifest_schema_version": "1.0.0",
  "deterministic_metadata": {
    "dataset_version": "v0.4_hard",
    "seed": 42,
    "canonical_id_format": "arkhe_v04:{seed}:{split}:{template_id}:{ground_truth_class}:{trajectory_index}",
    "source_code_provenance": {
      "commit_hash": "9e116263...",
      "branch": "feat/openai-grant-readiness-v0.3",
      "is_dirty": false,
      "uncommitted_files": []
    },
    "configuration": {
      "config_file": "configs/hard_dataset_v0.4.yaml",
      "config_sha256": "4b971a81..."
    },
    "environment": {
      "python_version": "3.11.9",
      "dependencies": {
        "pydantic": "2.12.5",
        "numpy": "2.4.2",
        "yaml": "6.0.3"
      }
    },
    "file_hashes_sha256": {
      "observations/development.jsonl": "...",
      "ground_truth/development_labels.jsonl": "...",
      ...
    }
  },
  "execution_run_metadata": {
    "generated_at_utc": "2026-09-30T20:00:00Z",
    "execution_duration_seconds": 0.28
  }
}
```

### Deterministic vs. Variable Fields
- **`deterministic_metadata`:** Guaranteed to be bitwise identical across repeated executions on the same commit and environment.
- **`execution_run_metadata`:** Contains dynamic run telemetry (`generated_at_utc`, `execution_duration_seconds`). These timestamp/performance metrics are deliberately excluded from deterministic equality comparisons.

---

## 6. Legacy Dataset Protection

- The legacy dataset `datasets/v0.3/` (comprising 65 trajectories) is an **immutable historical benchmark record**.
- The deterministic generator and verifier for `v0.4_hard` operate in isolated namespaces (`datasets/v0.4_hard/`).
- Unit tests (`tests/test_deterministic_reproduction.py`) explicitly assert that `datasets/v0.3/` remains unmodified and protected from accidental mutation or overwriting.

---

## 7. CI/CD Integration

Automated verification is enforced on every Pull Request and branch push via GitHub Actions in `.github/workflows/grant-benchmark.yml`:

```yaml
  deterministic-generation-and-reproducibility:
    name: Deterministic Dataset Generation & Provenance Audit
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Verify Deterministic Dataset Reproduction
        run: |
          python scripts/verify_deterministic_dataset_generation.py --check-tracked
      - name: Run Determinism Unit Tests
        run: |
          python -m unittest tests/test_deterministic_reproduction.py -v
```

---

## 8. Epistemic Limitations & Disclaimers

> [!IMPORTANT]
> **Deterministic Reproduction $\neq$ Scientific Generalization or Zero-Leakage**
> 
> Achieving 100% bitwise deterministic reproduction proves that the **generation pipeline is mathematically stable, non-flaky, and auditable**. However:
> 1. It does **not** prove that detectors evaluating this dataset are generalizable to out-of-distribution real-world LLM agent threats.
> 2. It does **not** replace blind evaluation: detectors must always remain strictly blinded to ground truth labels and event annotations.
> 3. Any change to prompt templates, scenario blueprints, or random seeds produces a new revision that must be versioned, audited, and cataloged independently.
