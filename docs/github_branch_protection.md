# Recommended GitHub Branch Protection Rules for `main`

To maintain scientific integrity, auditability, and reproducible research standards for the ARKHÉ Agent Boundary Defense Benchmark, the repository administrator should enforce the following branch protection rules on `main`:

---

## 1. Branch Protection Policy

Navigate to **Repository Settings** &rarr; **Branches** &rarr; **Add branch ruleset** (or **Branch protection rule**):
- **Branch pattern:** `main`

### A. Require a pull request before merging
- [x] **Require approvals:** At least 1 peer review approval.
- [x] **Dismiss stale pull request approvals when new commits are pushed:** Enabled.
- [x] **Require review from Code Owners:** Optional (or enabled if CODEOWNERS is defined).
- [x] **Require approval of the most recent reviewable push:** Enabled.

### B. Require status checks to pass before merging
- [x] **Require branches to be up to date before merging:** Enabled (ensures PR is tested against the latest `main`).
- [x] **Status checks required:**
  - `Unit Tests & Code Quality (Py 3.11)`
  - `Unit Tests & Code Quality (Py 3.12)`
  - `Anti-Leakage & Dataset Isolation Contracts`
  - `Reproducible Benchmark & Statistical Evaluation`
  *(All checks from `.github/workflows/grant-benchmark.yml`)*

### C. Block destructive actions
- [x] **Do not allow bypassing the above settings:** Enforce for Administrators.
- [x] **Restrict pushes:** Prevent direct pushes to `main`.
- [x] **Block force pushes:** Enabled (`--force` and `--force-with-lease` rejected).
- [x] **Block branch deletions:** Enabled.

### D. Cryptographic verification & linear history
- [x] **Require signed commits:** Enabled (GPG / SSH / S/MIME commit signing recommended).
- [x] **Require linear history:** Enabled (Squash and merge or Rebase and merge preferred).

---

## 2. Rationale for Grant Applications

1. **Experimental Traceability:** Prevents unverified commits or accidental history rewrites that could break the deterministic link between datasets, code, and published evaluation artifacts.
2. **Anti-Leakage Enforcement:** Guarantees that no PR introducing label leakage or breaking opaque ID anonymization can enter the canonical codebase.
3. **Reproducibility Guarantee:** Every state of `main` is provably verified by CI against both Python 3.11 and 3.12 without external secret dependencies.
