# Model Usage & API Integration Policy

This document details how OpenAI models and API endpoints are utilized within the ARKHÉ Agent Boundary Defense Benchmark.

---

## 1. Supported Model Families

The benchmark supports the following OpenAI model families via `OpenAISemanticClient`:

| Model Identifier | Role in Benchmark | Structured Outputs Support | Typical Latency |
| :--- | :--- | :--- | :--- |
| **`gpt-4o-mini`** (Default) | Fast, cost-efficient baseline for per-step semantic classification | Full (`json_schema` / Pydantic) | ~180–300 ms |
| **`gpt-4o`** | High-capacity reasoning baseline for subtle intent drift detection | Full (`json_schema` / Pydantic) | ~400–800 ms |
| **`o1` / `o3-mini`** | Advanced reasoning baseline for deep boundary violation analysis | Yes (via completion parsing) | ~1.5–4.0 s |

---

## 2. API Interaction Architecture & Schema

All API calls from `OpenAISemanticClient` enforce strict structured outputs using Pydantic schemas via the official OpenAI Python SDK (`openai>=1.30.0`):

```python
from pydantic import BaseModel, Field
from typing import Literal

class SemanticClassificationResponse(BaseModel):
    is_violation_risk: bool = Field(..., description="Whether this single step presents a boundary violation risk")
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(..., description="Assessed risk level")
    category: str = Field(..., description="Category of risk detected")
    reasoning: str = Field(..., description="Concise justification for the assessment")
```

Invocation snippet:
```python
response = self.client.beta.chat.completions.parse(
    model=self.model,
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ],
    response_format=SemanticClassificationResponse,
    temperature=0.0,
    seed=self.seed
)
```

---

## 3. Resiliency & Rate-Limit Handling

`OpenAISemanticClient` incorporates an automatic retry mechanism with exponential backoff to handle transient network issues and rate limits (`RateLimitError`, `APIConnectionError`):
- **Maximum Retries:** 2 (configurable).
- **Initial Delay:** 1.0 second, doubling on each subsequent retry ($1.0\text{s} \rightarrow 2.0\text{s}$).
- **Fail-Fast Policy:** If an API key is missing when `mode="openai_api"` is initialized, the client raises `ValueError` immediately rather than silently falling back.

---

## 4. Cost & Token Accounting

During execution, `harness/agent_benchmark_runner.py` records token consumption across every detector invocation:
- `prompt_tokens`: Cumulative input tokens consumed by the baseline prompt.
- `completion_tokens`: Output tokens generated for the structured classification.
- Estimated costs are computed using published OpenAI API rates and saved to `cost_report.json`.

---

## 5. Privacy & Data Minimization

- **No Sensitive Production Data:** No real customer data, personal information (PII), or production credentials are ever sent to the OpenAI API.
- **Sanitized Observation Inputs:** Inputs sent to the API contain only sanitized action names and synthetic tool arguments with mock values (`ARKHE_FAKE_TOKEN_DO_NOT_USE_*`).
