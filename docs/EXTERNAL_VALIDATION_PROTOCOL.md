# Retrospective External Validation Protocol

## Purpose

Evaluate ARKHÉ on an externally sourced but already closed incident without connecting to production or claiming live prevention.

The pilot answers one bounded question:

> Using only information available up to each point in time, does trajectory-aware analysis produce an earlier useful signal than the frozen isolated-event baseline without exceeding the pre-agreed false-alert tolerance?

## Eligible case

The case must:

- be closed and no longer require operational response;
- have an owner authorized to share a sanitized representation;
- contain an ordered sequence of at least five observable events;
- contain an independently documented outcome;
- permit removal of personal data, real credentials, account identifiers and sensitive payloads;
- involve no active target, exploit execution or live financial action.

Cases created solely by the ARKHÉ author are not external validation.

## Partner inputs

The partner provides:

1. a sanitized event sequence;
2. the incident or boundary outcome;
3. when the existing process first detected the issue;
4. the containment decision and timestamp, when available;
5. the fields that were genuinely available at each step;
6. a written statement authorizing the offline evaluation.

The partner does not need to disclose infrastructure names, customer identities or working secrets.

## Pre-run freeze

Before any scored execution, record:

- case identifier and data hash;
- eligible event fields;
- primary endpoint;
- baseline definition;
- detector versions;
- thresholds;
- maximum acceptable false-alert rate;
- success, inconclusive and failure criteria;
- reviewers;
- analysis exclusions;
- stopping conditions.

A test-informed change creates a new exploratory version and cannot repair the original confirmatory result.

## Execution

1. Validate authorization and sanitization.
2. Convert the case into the canonical observation contract.
3. Keep ground truth outside detector-visible inputs.
4. Replay events in original order.
5. Run the frozen baseline and ARKHÉ over identical observations.
6. Capture earliest signal, decision, evidence, latency, cost and missing context.
7. Repeat only according to the frozen protocol.
8. Ask the partner reviewer to assess factual correctness and operational usefulness.
9. Publish or retain only the evidence authorized by the partner.

## Primary measures

- lead time or lead steps relative to the independently recorded detection point;
- Task A recall for pre-violation anticipation, when applicable;
- false-positive rate over declared negative decisions;
- alert precision among reviewed alerts;
- proportion of insufficient-evidence decisions;
- context-loss rate;
- decision traceability;
- reviewer usefulness score with written rationale.

One case does not establish population-level accuracy. Report counts and case-level evidence, not generalized percentages without a valid denominator.

## Outcome classification

### Supports the hypothesis

ARKHÉ produces an earlier useful signal, respects the false-alert tolerance, and the independent reviewer confirms that the evidence would have been actionable.

### Weakens the hypothesis

ARKHÉ is later than the baseline, exceeds the false-alert tolerance, or produces explanations the reviewer considers misleading or unusable.

### Inconclusive

Instrumentation coverage, missing context, ambiguous ground truth or insufficient sample size prevents a defensible comparison.

Inconclusive is a valid result and must not be silently excluded.

## Safety and data rules

- no production credentials;
- no personal or payment-card data;
- no customer-facing actions;
- no active exploitation;
- no unapproved external destination;
- no publication without explicit authorization;
- stop if unexpected sensitive data appears.

## Deliverables

- authorization record;
- sanitized case manifest;
- immutable input hash;
- baseline and detector manifests;
- predictions and decision evidence;
- evaluation report;
- partner review;
- limitations and deviations;
- retention or deletion confirmation.

## Advancement rule

A successful internal rehearsal closes only G1. An unaffiliated reproduction closes G2. A partner-owned retrospective case is required for G3. Shadow deployment is a separate authorization decision.
