# Security Policy

## Defensive Research Objective
ARKHÉ is an applied defensive research benchmark created to measure early detection of security boundary violations, mission drift, and prompt injection propagation in autonomous AI agents.

## Synthetic Data & Zero Real Credential Guarantee
All datasets, scenario templates, tokens, and endpoints included in this repository are strictly synthetic:
- Tokens follow synthetic patterns such as `ARKHE_FAKE_TOKEN_DO_NOT_USE_*`.
- Network endpoints target local mock sinks (e.g., `http://localhost:8080/mock-sink` or `https://internal.secops.test`).
- No proprietary corporate data or live credentials are used or retained.

## Dual-Use & Harm Mitigation Policy
The ARKHÉ benchmark is exclusively defensive:
1. **No Weaponized Payloads:** Scenario templates provide behavioral descriptions and abstract structural traces rather than functional zero-day exploit payloads.
2. **Defensive Metrics:** The evaluation suite measures detector precision, recall, false positive rates, and early warning lead time ($N_{\text{lead}}$), providing defensive teams with quantitative criteria for guardrail selection.
3. **Auditability:** Ground truth labels and detector predictions are strictly separated to prevent circularity and enable independent audit.

## Reporting a Vulnerability
If you discover a security vulnerability or sensitive information leakage in this repository:
1. Do **not** open a public GitHub issue.
2. Email the maintainer at `security@arkhe-benchmark.org` or report via GitHub Private Vulnerability Reporting.
3. Include detailed steps to reproduce, the commit hash, and the potential impact.
4. You will receive an initial response within 48 hours.
