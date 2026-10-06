# Security Policy

## Supported Versions

The following table lists which versions of the ARKHÉ Agent Boundary Defense Benchmark receive active security support and bug fixes:

| Version | Supported          | Status                               |
| ------- | ------------------ | ------------------------------------ |
| 0.3.x   | :white_check_mark: | Active Candidate (Grant Evaluation)  |
| 0.2.x   | :x:                | Superseded (Legacy pilot)            |
| < 0.2.0 | :x:                | Deprecated                           |

---

## Reporting a Vulnerability

The ARKHÉ research team takes the security of agent evaluation environments seriously. If you discover a vulnerability in the benchmark harness, evaluation framework, detector contracts, or data isolation mechanisms, please report it privately.

### Preferred Method
- **GitHub Security Advisory:** Navigate to the repository's **Security** tab and click **Report a vulnerability**. This allows secure, private disclosure directly to project maintainers.
- **Direct Contact:** If GitHub Security Advisories are unavailable, email the lead researcher at `kizua@creusio.org` with the subject line `[SECURITY] ARKHÉ Vulnerability Report`.

### What to Include in Your Report
1. A clear description of the vulnerability (e.g., code injection in runner, environment variable exfiltration, contract bypass, or label leakage vector).
2. Step-by-step instructions or a minimal reproducible proof-of-concept (PoC).
3. The affected component, file, and commit hash.
4. Any potential mitigations or patches you have identified.

### Response Timeline
- **Initial Acknowledgement:** Within **48 hours**.
- **Triage & Assessment:** Within **5 business days**.
- **Remediation & Patch Release:** Target within **30 calendar days**, coordinated under responsible disclosure.

---

## Out of Scope
The following items are intentional research features and **not** considered reportable vulnerabilities:
- **Synthetic Attack Datasets:** Files within `datasets/` intentionally simulate prompt injection, privilege escalation, and tool misuse using harmless synthetic payloads and fake tokens (`ARKHE_FAKE_TOKEN_DO_NOT_USE_*`).
- **Simulated Tool Sandboxes:** Mock network endpoints (such as `http://localhost:8080/mock-sink`) that record requests without executing real-world commands.

## SDK alpha scope

The independent SDKs0.2.0 are experimental. The benchmark version-support table above does not describe SDK version support. SDK recovery uses plaintext SQLite under a trusted host, a protected directory and one owner per journal. Hashes detect accidental corruption, not malicious storage edits. Host authentication, tool isolation, retention and historical policies remain integration responsibilities.

A monitored private reporting channel and any response commitment for the SDKs require confirmation by the maintainer before their release. No SDK response SLA or production support commitment is established here. Report only sanitized reproductions; never include real credentials or customer data in public issues.
