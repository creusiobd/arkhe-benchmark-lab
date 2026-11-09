# External Validation Gates

This document prevents laboratory evidence from being represented as production validation. Each gate must be closed with traceable artifacts. A later gate cannot compensate for a failed earlier gate.

## Claim levels

| Level | Allowed claim | Prohibited claim |
|---|---|---|
| L0 — Design | The method is specified | The method works |
| L1 — Internal laboratory | The implementation is reproducible on project-authored synthetic data | External generalization or operational effectiveness |
| L2 — Independent reproduction | A third party reproduced the declared laboratory result | Production effectiveness |
| L3 — Retrospective external pilot | The method was evaluated on an externally sourced, sanitized, closed incident | Prevention in live operation |
| L4 — Authorized shadow | The method observed a live eligible flow without controlling it | Automated prevention or safe autonomous action |
| L5 — Controlled enforcement | An authorized host enforced bounded decisions under explicit rollback controls | General safety outside the evaluated scope |

## G0 — Truthful evidence inventory

**Exit criteria**

- README and proposal distinguish historical, exploratory, prospective, and confirmatory artifacts.
- Every result names dataset, commit, model, mode, split and claim status.
- Synthetic, internal and externally sourced evidence are never pooled.
- Known test-informed datasets cannot be relabeled as untouched holdouts.

**Current status:** partially satisfied.

## G1 — Reproducible internal study

**Exit criteria**

- One primary hypothesis and one primary endpoint are frozen.
- Dataset, split, scoring code, configuration and thresholds are hashed.
- Baselines and ARKHÉ receive the same detector-visible observations.
- Calibration uses validation data only.
- Test results include raw numerators, denominators and uncertainty.
- A clean checkout reproduces the evidence package.
- Failures and high false-positive outcomes remain visible.

**Required artifacts**

- protocol;
- freeze manifest;
- run manifest;
- predictions;
- evaluation;
- cost report;
- limitations;
- integrity verification output.

**Current blocker:** the prospective v0.5 implementation is not integrated with the current `main`.

## G2 — Independent reproduction

**Exit criteria**

- A reviewer not involved in detector tuning runs the package without private instructions.
- Environment and deviations are recorded.
- Artifact hashes match or justified differences are documented.
- The reviewer can reconstruct at least one decision from inputs to evidence.
- The reproduction result is retained even if it fails.

**Current blocker:** no independent reviewer or signed reproduction record.

## G3 — Retrospective external pilot

**Exit criteria**

- A partner supplies an already closed incident or workflow-derived case.
- Data is sanitized and authorized before transfer.
- Ground truth comes from partner evidence, not ARKHÉ output.
- The baseline and acceptance thresholds are frozen before evaluation.
- No production connection, real credential or live financial action is used.
- The partner reviews usefulness and factual accuracy.
- The report states whether the outcome supports, weakens or leaves the hypothesis unresolved.

**Current blocker:** no external case owner or letter of intent.

## G4 — Authorized shadow observation

**Exit criteria**

- Environment, data and security owners approve scope, retention and shutdown.
- Observation is read-only and cannot grant tools or permissions.
- Data allowlists, minimization and deletion are tested.
- Coverage, context loss and overhead are measured.
- Adversarial injection in production requires separate explicit authorization.
- A rollback and incident contact are named.

**Current blocker:** G3 is not closed.

## G5 — Partner or production readiness

**Exit criteria**

- At least one external pilot has measurable, reviewable results.
- The service boundary, support model and responsibility matrix are defined.
- Security, privacy, legal and operational risks have owners.
- Customer need and deployment path are evidenced.
- Claims match the narrow evaluated scope.

**Current blocker:** no validated external delivery capability.

## Decision rule

Daybreak partner positioning is not permitted before G3. Production-effectiveness language is not permitted before G4. Bug bounty submission requires a real in-scope product control failure; benchmark behavior alone remains research evidence.
