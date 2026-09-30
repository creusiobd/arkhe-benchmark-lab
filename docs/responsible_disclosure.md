# Responsible Disclosure & Dual-Use Research Policy

The ARKHÉ Agent Boundary Defense Benchmark is committed to the ethical advancement of AI security. Our research aims to equip defenders with robust, open-source measurement tools and early-warning mechanisms without releasing weaponized attack vectors.

---

## 1. Defensive Orientation & Dual-Use Assessment

AI safety benchmarks inherently touch on adversarial capabilities. To ensure our work strictly benefits defenders, ARKHÉ enforces four non-negotiable safeguards:

1. **Abstracted Behavioral Patterns:** Trajectories evaluate the causal sequence of capability expansion and intent drift at the telemetry level, rather than publishing weaponized zero-day exploits.
2. **Synthetic Mock Entities:** All credentials, API keys, hostnames, and IP addresses within the benchmark are explicitly synthetic (`ARKHE_FAKE_TOKEN_DO_NOT_USE_*`, `localhost`, `mock-sink`).
3. **No Unsanitized Malicious Payloads:** Prompt injection templates in `datasets/` represent high-level conceptual bypasses (e.g., instructional override formats) widely documented in academic literature, avoiding proprietary or destructive payloads.
4. **Defender-Centric Measurement:** The primary output of the benchmark is measuring defensive anticipation ($N_{\text{lead}}$) and false positive reduction, directly assisting organizations in hardening agent boundaries.

---

## 2. Coordinated Disclosure Procedure

If during red-teaming campaigns or dataset development the ARKHÉ team or external contributors identify a novel, unmitigated vulnerability in an LLM agent framework, tool integration, or foundation model:

1. **Immediate Embargo:** The finding is placed under a strict embargo. No public dataset inclusion, commit, or preprint disclosure will occur until coordinated disclosure is complete.
2. **Vendor Notification:** We will contact the affected vendor’s security team (e.g., OpenAI Security, LangChain Security, Hugging Face) providing:
   - Technical description of the vulnerability.
   - Minimal reproducible proof-of-concept.
   - Proposed defensive telemetry and detection signatures.
3. **Disclosure Timeline:** Standard 90-day coordinated disclosure period, with potential extension if a fix requires significant architectural changes.
4. **Advisory Credit:** Public reports will credit researchers and vendors collaboratively upon release of defensive patches.

---

## 3. Contact for Ethical & Disclosure Inquiries

For questions regarding dual-use evaluation, responsible disclosure coordination, or security concerns, contact:
- **Lead Researcher:** Creúsio Adolfo Gaspar Kizua (`kizua@creusio.org`)
- **Repository Security:** Submit via private GitHub Security Advisory.
