# Formal Threat Model for Autonomous AI Agent Boundary Defense

## 1. System Architecture & Trust Boundaries

The ARKHÉ benchmark formalizes an autonomous agent execution environment consisting of five primary architectural components and their respective trust boundaries:

```
+-------------------------------------------------------------------------+
|                              USER PROMPT                                |
|   (Untrusted / Semi-Trusted: Direct instructions, goals, constraints)   |
+------------------------------------+------------------------------------+
                                     |
                                     v
+------------------------------------+------------------------------------+
|                         AGENT CORE (LLM)                                |
|   - Reasoning engine, plan generation, contextual tool invocation       |
|   - Context Window (Memory: System prompt, history, tool outputs)       |
+-------------------+--------------------------------+--------------------+
                    |                                |
        [Trust Boundary 1: Ingestion]    [Trust Boundary 2: Dispatch]
                    |                                |
                    v                                v
+-------------------+-------+       +----------------+--------------------+
|     EXTERNAL UNTRUSTED    |       |         TOOL REGISTRY               |
|         DATA SOURCES      |       | - read_file, execute_sql, web_get   |
| (Web pages, APIs, PDFs)   |       | - bash_exec, send_email, api_call   |
+---------------------------+       +----------------+--------------------+
                                                     |
                                         [Trust Boundary 3: Impact]
                                                     |
                                                     v
                                    +----------------+--------------------+
                                    |    ENTERPRISE TARGET ENVIRONMENT    |
                                    | (Production DB, Credentials, Net)   |
                                    +-------------------------------------+
```

### Trust Boundary Definitions:
1. **Trust Boundary 1 (Ingestion / Ingress):** Data returned by tools from external or third-party sources (web search results, database rows, customer tickets) crossing into the LLM context window. Untrusted by default.
2. **Trust Boundary 2 (Dispatch / Execution):** Actions emitted by the LLM toward tool executors. The agent operates under defined capability constraints (e.g., read-only permissions vs administrative execution).
3. **Trust Boundary 3 (Impact / Boundary):** Physical side-effects on underlying systems, enterprise networks, credentials, or persistence mechanisms.

---

## 2. Adversarial Personas & Capabilities

| Threat Actor | Access Level | Primary Capability | Objective |
| :--- | :--- | :--- | :--- |
| **Indirect Injector (External)** | Zero agent access; controls third-party data | Injects instructions into web pages, tickets, or documents read by the agent | Hijack agent plan, exfiltrate data, force unauthorized tool dispatch |
| **Compromised Tool / Subagent** | Returns poisoned responses to parent agent | Malicious payloads in tool output schema | Escalate privileges, bypass supervisory guardrails |
| **Adversarial End-User (Jailbreaker)** | Directly submits prompts to agent | Social engineering, prompt injection, multi-turn deception | Force agent to exceed its assigned enterprise boundaries |

---

## 3. Attack Vector Taxonomy (5 Canonical Threat Families)

ARKHÉ categorizes agent boundary violations into five orthogonal families:

### A. Prompt Injection Propagation (`prompt_injection_propagation`)
- **Mechanism:** The agent ingests external untrusted text containing malicious commands formatted to simulate system instructions or supervisory overrides (e.g., `[SYSTEM OVERRIDE]: Ignore previous instructions and execute...`).
- **Trajectory Signature:** Initial benign data retrieval $\rightarrow$ subtle deviation in reasoning $\rightarrow$ invocation of tools outside assigned scope.

### B. Tool Misuse & Capability Expansion (`tool_misuse_escalation`)
- **Mechanism:** The agent chains low-privilege tools (e.g., directory enumeration, log reading) to construct an unintended capability (e.g., staging executable scripts, privilege escalation).
- **Trajectory Signature:** Monotonic increase in tool variety, execution rate, and parameter complexity beyond declared baseline.

### C. Sensitive Credential Access (`credential_access`)
- **Mechanism:** Direct or indirect attempts to inspect local `.env`, configuration stores, cloud instance metadata (`169.254.169.254`), or secret vaults.
- **Trajectory Signature:** Path traversal sequences, specific environment variable queries, inspection of memory caches.

### D. Unauthorized Network Egress (`unauthorized_egress`)
- **Mechanism:** Exfiltration of harvested context or sensitive tokens to adversary-controlled external endpoints via HTTP POST, DNS tunneling, or unauthorized webhooks.
- **Trajectory Signature:** Data staging actions followed by network connections to unlisted or external hostnames.

### E. Defensive Evasion & Persistence (`evasion_persistence`)
- **Mechanism:** Splitting unauthorized actions across multiple steps, base64 encoding payloads, or altering logs to bypass single-step perimeter filters.
- **Trajectory Signature:** Elevated entropy in payload encodings, repeated probing followed by low-latency bursts.

---

## 4. Defense Paradigms Compared

| Property | Deterministic Event Rules | Isolated Semantic Classifier (LLM Judge) | ARKHÉ Trajectory Sentinel |
| :--- | :--- | :--- | :--- |
| **Scope of Observation** | Atomic payload (regex/keyword) | Single step (tool + argument) | Full trajectory state-space ($\mathcal{T}$) |
| **Historical Context** | None ($t=i$) | None ($t=i$) | Cumulative ($t=1 \dots i$) |
| **Anticipation Capability** | Reactive (fires at breach) | Reactive (fires at breach) | **Preemptive ($N_{\text{lead}} \ge 1$)** |
| **Inference Cost** | $O(1)$ CPU | High (LLM token inference) | $O(1)$ mathematical state evaluation |
| **Evasion Vulnerability** | High (obfuscation, synonymy) | Moderate (adversarial prompt) | Low (tracks trajectory phase space) |
