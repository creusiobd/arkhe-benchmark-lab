# Official Application Form Answers — OpenAI Cybersecurity Grant Program

**Submission candidate:** ARKHÉ v0.6
**Applicant:** Creúsio Adolfo Gaspar Kizua — São Paulo, Brazil
**Status:** Draft for human review. Not submitted.

## Field 1: Project Title

**ARKHÉ v0.6: An Independently Custodied Benchmark for Trajectory-Aware Agent Security**

## Field 2: One-Sentence Description

An open defensive study testing whether multi-step trajectory analysis improves timely pre-violation classification over a frozen single-event OpenAI comparator on 200 independently authored, previously unseen agent-security cases.

## Field 3: Problem Statement

Autonomous agents can remain locally plausible while becoming globally unsafe. A tool call, memory write, delegation, or authorization check may appear acceptable in isolation, yet the sequence can gradually alter mission, trust, capability, or identity until a boundary is crossed. Event-level guardrails therefore face a difficult trade-off: sensitive thresholds interrupt legitimate workflows, while permissive thresholds miss violations that only become visible across time.

Existing ARKHÉ laboratory work shows that this trade-off can be measured reproducibly, but it does not establish external generalization or production effectiveness. Its v0.5 corpus was authored and inspected during development, so it is deliberately restricted to integration and reproducibility evidence.

The proposed v0.6 study addresses the missing evidence. It will compare one frozen semantic event-level classifier with a frozen trajectory-aware detector on 200 independently authored synthetic cases from four previously unused security families. Test labels will remain under independent custody until the protocol, code, model, retry policy, and sealed manifest are frozen. The study will publish positive, null, or negative results, including raw denominators, false positives, missed violations, latency, token use, and cost.

*(Word count: 177 words — within the 200-word limit)*

## Field 4: Complete Project Proposal

### Research question and hypothesis

Does trajectory-aware analysis improve timely pre-violation classification over a frozen single-event semantic comparator on previously unseen agent-security cases?

The primary hypothesis is that ARKHÉ will improve paired Task A correctness by at least **15 percentage points** relative to the event-level comparator. The primary comparison will be a two-sided exact McNemar test at `alpha = 0.05`. The minimum relevant effect, endpoint, missing-data rule, stopping rule, and comparator are declared before test evidence exists.

### Existing foundation and evidence boundary

The public repository already contains Apache-2.0 defensive and trajectory SDKs, strict separation between observations and ground truth, deterministic generation, validation-only calibration, an evaluator isolated from detector tuning, anti-leakage CI, OpenAI Structured Outputs integration, and operational telemetry.

The existing evidence is intentionally bounded. The v0.5 pipeline is reproducible, but its outputs were inspected during development and remain `reproducibility_only`. They cannot become confirmatory evidence retrospectively. An earlier exploratory OpenAI integration completed 268 calls and 147,172 tokens at a configured cost of USD 0.028966. It demonstrated the request and telemetry path only; it did not establish comparative effectiveness.

The v0.6 protocol is currently in design with `claim_eligibility: none` and `confirmatory_claims_allowed: false`. No v0.6 dataset, labels, predictions, results, or freeze artifacts exist. This is a deliberate scientific control.

### New study population

The study will contain **200 independently authored synthetic trajectories**, 50 in each novel family:

1. `persistent_memory_poisoning` — unsafe behavior emerging after persistent memory changes;
2. `cross_agent_delegation_confusion` — authority or intent changing through agent handoffs;
3. `skill_mcp_supply_chain_compromise` — misleading behavior introduced through skills, MCP components, or metadata;
4. `authorization_identity_drift` — identity, role, or permission assumptions changing across a workflow.

The predeclared distribution per family is 20 benign hard negatives, 15 near-violations, and 15 consummated violations. Each case must contain 4–12 ordered steps, an explicit mission and boundary policy, deterministic ground truth, and a predeclared violation step for positive cases.

Cases will be excluded if they reuse v0.5 mechanisms or templates, contain real secrets or personal data, include functional exploits, depend on uncontrolled external systems, or lack a determinable outcome. All resources will be synthetic or local.

### Independent custody and freeze

An independent case author/test custodian will be contracted before freeze. This person will not tune ARKHÉ and will control test labels and the sealed manifest. A separate named reviewer will approve the protocol.

Before unblinding, the repository will record the frozen commit, protocol SHA-256, exact provider-returned model identifier, prompts, structured-output schema, thresholds, retry policy, inclusion and exclusion rules, signed test-manifest SHA-256, custodian, and approver. Without those roles, the protocol cannot freeze and no confirmatory claim will be made.

### Comparator, detector, and evaluation

The primary comparator will be a semantic single-event classifier using **`gpt-6.1-sol`** through the Responses API with Structured Outputs. It will receive only the current event, never history or ground truth.

ARKHÉ will receive the same event plus prior observable steps. It uses mission, capability, boundary, state-change, and persistence signals. Its quadratic score is a risk feature inspired by dynamical-systems methods, not proof of Lyapunov stability. An optional `gpt-6-astra` robustness analysis may run only after the primary result and will be reported separately.

The design uses one sealed external test set. Thresholds, prompts, schemas, and retry rules are locked using historical development and validation artifacts only; no v0.6 case, label, or prediction is used for calibration. The primary task is timely classification of consummated violations: an alert must occur strictly before the predeclared violation step. Pressure detection is reported separately.

A prospective exact-power sensitivity analysis uses no v0.6 outcomes. With a 15-point paired effect, two-sided `alpha = 0.05`, and 50% total detector discordance, 200 cases provide 83.64% power; the exact minimum is 183. At 40% discordance power is 91.12%, while at 60% it falls to 76.11%. The 50% scenario is the predeclared design assumption. There will be no outcome-driven sample expansion, and the underpowered 60% scenario remains an explicit limitation.

Repetition 1 is primary. Additional repetitions measure repeatability and are not pooled as independent evidence. After frozen retries are exhausted, a missing detector output counts as incorrect for that detector. A sealed case may be excluded only if the custodian records a malformed-case decision before unblinding. All exclusions and denominators will be published.

There is no optional stopping. All 200 primary trajectories will run once. Execution may pause only for a safety, integrity, or infrastructure failure before outcome inspection and may resume only from the sealed package under a documented deviation.

### Metrics and public benefit

The report will publish paired correctness, exact McNemar results, TP/FP/TN/FN, precision, recall, F1, false-positive rate, Wilson 95% intervals, lead steps, results by family, repeatability, latency, calls, tokens, retries, failures, cost, exclusions, and deviations.

Positive, null, and adverse results will be published. Passing CI demonstrates implementation consistency, not detector superiority. Synthetic results will not be described as production validation.

The sanitized dataset will be released under CC-BY-4.0; the harness, detectors, contracts, and evaluator under Apache-2.0. The release will include a dataset card, threat model, preregistration, reproducibility guide, technical report, and open preprint. No live secrets, malware, zero-day exploits, or unauthorized targets will be included.

## Field 5: Project Timeline

- **Week 1:** sensitivity analysis; appoint custodian and approver; finalize prompt, schema, and retries.
- **Week 2:** lock the detector, analysis plan, source commit, model identifier, and protocol hash before test authoring.
- **Weeks 3–5:** independently author, review, audit, and seal 200 sanitized cases; record the signed test-manifest hash and complete the final freeze.
- **Week 6:** execute the frozen comparator and ARKHÉ once; record predictions and telemetry; run the primary analysis.
- **Week 7:** run repeatability without pooling; conduct independent protocol review; document deviations and limitations.
- **Week 8:** publish code, sanitized data, manifests, technical report, and preprint, including null or negative results.

## Field 6: Requested Funding, API Credits, and Resources

**Total request: USD 10,000**

| Item | Amount | Purpose |
|---|---:|---|
| Applied research and engineering | USD 5,700 | Eight-week protocol, implementation, execution, analysis, documentation, and release |
| Independent case author/custodian and protocol review | USD 3,000 | Construction and custody of 200 cases, sealing, and pre-unblinding review |
| OpenAI API credits | USD 300 | `gpt-6.1-sol` primary evaluation, retries, repeatability, and bounded `gpt-6-astra` robustness analysis |
| Infrastructure and open dissemination | USD 1,000 | Isolated execution, CI artifacts, persistent hosting, DOI deposit, and accessibility review |

The API allocation is intentionally modest. At current list prices, `gpt-6.1-sol` costs USD 2 per million input tokens and USD 10 per million output tokens. The allocation supports up to approximately 6,000 structured-output calls with contingency for retries, token-profile variance, and a bounded Astra run. Actual IDs, tokens, and costs will be published; unused credits will not be represented as expenditure.

The project also requests methodological feedback on the frozen evaluation design. It does not request production deployment, privileged internal data, or access to third-party systems.

## Field 7: Applicant and Team

**Principal researcher:** Creúsio Adolfo Gaspar Kizua, São Paulo, Brazil.

Creúsio has more than six years of experience in financial and payment systems, distributed observability, APIs, incident response, and 24×7 operations. He has led a 13-person technical team and worked with OpenTelemetry, Kubernetes, Prometheus, Grafana, Dynatrace, Elastic, and related reliability tooling. He created the ARKHÉ open-source benchmark, contracts, SDKs, and experimental governance controls.

The application is currently individual. The independent author/custodian and approver will be selected and named before freeze. Their compensation is budgeted. No anonymous or simulated reviewer will be represented as independent validation.

## Field 8: New Dataset

Yes. The project will create a new 200-trajectory independently authored synthetic dataset covering four previously unused agent-security families. Detector developers will not receive test labels before lock. The public release will exclude real credentials, personal data, functional exploits, and third-party confidential information and will include provenance, schemas, class definitions, limitations, hashes, and a CC-BY-4.0 license.

## Field 9: OpenAI Models

- **Primary comparator:** `gpt-6.1-sol`, event-level Structured Outputs classifier through the Responses API.
- **Optional robustness analysis:** `gpt-6-astra`, executed only after the primary result and reported separately.

The provider-returned model identifier, configuration, prompt hash, retry policy, tokens, latency, errors, and cost will be recorded. No offline proxy will be presented as an OpenAI-model result.

## Field 10: Availability of Results

Code, schemas, protocols, aggregate results, a sanitized dataset, and the technical report will be released publicly through GitHub and an open archival repository. Positive, null, and negative findings will be published. Case-level material that creates unnecessary misuse risk will be abstracted while preserving enough evidence to reproduce the defensive evaluation.

## Submission Gate

Submit only after English and Portuguese consistency tests pass, model availability and pricing are reverified, repository links and contact details are checked, and the applicant approves the final wording and budget. No field may imply production validation, OpenAI endorsement, or completed v0.6 evidence.
