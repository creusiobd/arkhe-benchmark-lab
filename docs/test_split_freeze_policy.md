# ARKHÉ Benchmark — Test Split Freezing Rule & Scientific Integrity Protocol

## 1. Context and Motivation

In benchmark science for AI systems and cybersecurity defenses, a major threat to validity is **test set leakage and detector calibration**. When a defense system's hyperparameters (such as risk thresholds $\theta$, embedding weights $W$, decay factors $\lambda$, or lexical heuristics) are adjusted after observing failure cases on the test split, the resulting metrics cease to be a measure of genuine out-of-distribution generalization. Instead, they reflect adaptive overfitting to specific test observations.

To ensure that the ARKHÉ Agent Boundary Defense Benchmark meets the audit standards of the **OpenAI Cybersecurity Grant Program**, this document establishes the binding **Test Split Freezing Protocol**.

---

## 2. The Freezing Rule (Regra de Congelamento do Test Split)

1. **Permanent Freeze of Test Partition:**
   The test split (`datasets/v0.4_hard/observations/test.jsonl` and `datasets/v0.4_hard/ground_truth/test_labels.jsonl`) is cryptographically sealed and permanently frozen as of commit date September 30, 2026.

2. **Permissible Use of Partitions:**
   - **`development` split:** May be used freely for exploratory prompt engineering, exploratory error analysis, and detector prototype development.
   - **`validation` split:** Reserved exclusively for model selection and hyperparameter tuning (e.g., establishing optimal threshold $\theta$ on ROC/PR curves).
   - **`test` split:** Must be executed **only once** as a terminal evaluation run. It must NEVER be used to back-tune detectors, modify embedding kernels, or adjust rules.

3. **Mandatory Version Bumping upon Test-Driven Modifications:**
   If a detector, feature extraction logic, or baseline implementation is modified in response to observations or errors identified on the test split:
   - The test run cannot be claimed as an "unseen holdout evaluation" or "zero-shot generalization".
   - A new version of the benchmark must be formally created (`v0.5+`), and new distinct test families/scenarios must be generated under a new random seed.

4. **Internal Held-Out Scope vs External Evaluation:**
   Because this repository is open source under the Apache-2.0 license, all files reside in the same public git tree. Therefore, we explicitly and scientifically delimit our claims:
   > **Scientific Boundary:** The test split represents an **internal family-held-out evaluation set** (conjunto de teste interno retido por família inteira). It is strictly disjoint in threat families and operational mechanisms from the development and validation splits. However, because the repository is open source, local retention does not constitute an external, air-gapped, third-party blind audit. Future independent evaluations will be performed on an unreleased external benchmark corpus ($N=5,000+$).

---

## 3. Cryptographic Hashes of Sealed Datasets

| Dataset Partition | File Path | SHA-256 Checksum | Trajectories | Status |
| :--- | :--- | :--- | :---: | :---: |
| **v0.4_hard Development Obs** | `datasets/v0.4_hard/observations/development.jsonl` | `acd0d2917ddd847a89337d1e7aa10bf9d88dd088d4214b5afd710a9f29f0a85a` | 20 | FROZEN |
| **v0.4_hard Development GT** | `datasets/v0.4_hard/ground_truth/development_labels.jsonl` | `4e96da999145a499dcd9f803496570d6d7501371628d0eaca4428cf6a2adb939` | 20 | FROZEN |
| **v0.4_hard Validation Obs** | `datasets/v0.4_hard/observations/validation.jsonl` | `3c9e50310a8a028e4c8c1f78a2671bfff5a56129886f052a864299c7e7aa4876` | 10 | FROZEN |
| **v0.4_hard Validation GT** | `datasets/v0.4_hard/ground_truth/validation_labels.jsonl` | `4f34c4a8f6f6f05e963fc9264640bfbf7474edde8c5857d3a46484bd677d8e36` | 10 | FROZEN |
| **v0.4_hard Test Obs** | `datasets/v0.4_hard/observations/test.jsonl` | `9ee500f89c2fb89ebb4db2d63bacb31006e6693b124bbb34d6a955beb331c7cc` | 20 | **PERMANENTLY SEALED** |
| **v0.4_hard Test GT** | `datasets/v0.4_hard/ground_truth/test_labels.jsonl` | `f766abbc704a21205fce6cf80f0b4287d8fa755fce86fc2055243152322b42ce` | 20 | **PERMANENTLY SEALED** |

---

## 4. Verification

Integrity of the frozen partitions is automatically verified in continuous integration by [`tests/test_hard_dataset_integrity.py`](../tests/test_hard_dataset_integrity.py). Any unauthorized mutation of frozen records will immediately fail CI.
