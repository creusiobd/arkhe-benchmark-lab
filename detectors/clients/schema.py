"""
Structured schema for semantic event classification responses.
==============================================================
Enforces typed structured output from both the OpenAI API and offline heuristic proxy.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class SemanticClassificationResponse(BaseModel):
    """
    Standardized semantic verdict for an isolated step observation.
    Compatible with OpenAI's structured outputs via response_format.
    """
    predicted_class: str = Field(
        ...,
        description="Classification verdict: 'benign', 'near_violation', or 'violation'"
    )
    is_alert: bool = Field(
        ...,
        description="Whether this observation triggered a security boundary alert"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Classifier confidence score in [0.0, 1.0]"
    )
    security_reasons: List[str] = Field(
        default_factory=list,
        description="Auditable security rationale indicators explaining the verdict"
    )
    violation_step_index: Optional[int] = Field(
        None,
        description="Observed step index if an explicit violation was detected"
    )
