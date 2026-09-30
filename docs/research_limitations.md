# Research Limitations & Honest Boundary Disclosures

Scientific integrity requires transparently communicating the boundaries, limitations, and underlying assumptions of our benchmark and defensive methodology. ARKHÉ does not claim total immunity or flawless defense; our claims are strictly bounded by empirical evidence.

---

## 1. Synthetic Execution Traces

### Limitation
The trajectories in `datasets/v0.3/` (and the pilot dataset) are synthetically generated sequences based on formalized agent execution schemas, real-world CVE patterns, and the OWASP Top 10 for LLM Applications. While they accurately reflect tool call arguments, raw observations, and thought traces, they are not recorded from live execution inside interactive operating system sandboxes.

### Impact & Planned Remediation
- Synthetic traces may underrepresent the unstructured noise, network timeouts, and non-deterministic formatting typical of production environments.
- **Grant Milestone:** With grant funding (Tier A/B), we will deploy containerized execution harnesses (Docker/Firecracker microVMs) to capture live agent interactions running real OS-level tools.

---

## 2. Deterministic Offline Proxy vs. Live Frontier Model Nuance

### Limitation
For hermetic reproducibility and zero-cost CI validation, the benchmark includes an `offline_proxy` mode in `SemanticEventDetector`. Although the proxy emulates the structured output and classification categories of `OpenAISemanticClient`, it employs deterministic heuristic matching rather than dynamic deep reasoning.

### Impact & Planned Remediation
- The proxy does not exhibit temperature-induced variance or the nuanced contextual understanding of live frontier models (`gpt-4o`, `o1`).
- The repository provides a tested, production-ready `OpenAISemanticClient` that executes live structured completions (`client.beta.chat.completions.parse`). Full live API evaluations across large trajectory sets will be performed using OpenAI API grant credits.

---

## 3. Trajectory Length & Time Horizons

### Limitation
The pilot trajectories feature average sequence lengths of 5 to 7 steps per trajectory, with a maximum of 10 steps. Real-world enterprise agent workflows can span dozens or hundreds of steps across long time horizons.

### Impact & Planned Remediation
- Short horizons may compress the velocity and acceleration metrics used by trajectory sentinels.
- Future benchmark iterations will incorporate long-horizon tasks (30–100 steps) requiring persistent memory and multi-session state tracking.

---

## 4. Single-Agent vs. Collaborative Multi-Agent Swarms

### Limitation
Version v0.3 benchmarks an autonomous agent operating individually against a tool registry and external data sources. It does not yet evaluate multi-agent swarms where boundary breaches propagate across inter-agent communication channels (e.g., supervisor-worker hierarchies).

### Impact & Planned Remediation
- Collaborative multi-agent attacks (e.g., untrusted subagent poisoning the shared memory pool) introduce distinct coordination dynamics.
- Tier B of the grant proposal directly funds expanding ARKHÉ to multi-agent swarm boundary defense.

---

## 5. Scope of Protection & Failure Modes

### Explicit Non-Claims:
1. **Single-Step Zero-Day Exploits:** If an adversary issues an atomic, single-step prompt injection that achieves immediate critical compromise in step 1 without preceding drift or exploratory tool calls, trajectory defense degenerates to single-step inspection.
2. **"Zero False Positives" Non-Claim:** No statistical classifier achieves zero false positives across arbitrary distributions. We report empirical false positive counts, exact confusion matrices, and Wilson score 95% confidence intervals.
3. **Cryptographic Guarantees:** When we refer to "cryptographic integrity" or "sealed ground truth", we refer to SHA-256 data integrity hashing and blind evaluation separation, not formal cryptographic zero-knowledge proofs.
