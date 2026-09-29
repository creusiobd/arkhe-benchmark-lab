"""
ARKHÉ Agent Boundary Defense Benchmark — Prediction Contract
============================================================
Defines the output produced by defensive detectors when evaluating observable steps.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class PredictedClass(str, Enum):
    BENIGN = "benign"
    NEAR_VIOLATION = "near_violation"
    VIOLATION = "violation"


class StepPrediction(BaseModel):
    """Prediction and feature scores emitted by a detector for a single step."""
    step_index: int = Field(..., ge=0, description="Step index evaluated")
    is_alert: bool = Field(..., description="Whether this step triggered an alert")
    predicted_class: Optional[PredictedClass] = Field(None, description="Step-level predicted class if applicable")
    mission_divergence_score: float = Field(0.0, ge=0.0, le=1.0, description="Inferred mission divergence [0, 1]")
    contamination_probability: float = Field(0.0, ge=0.0, le=1.0, description="Inferred prompt injection probability [0, 1]")
    boundary_proximity: float = Field(0.0, ge=0.0, le=1.0, description="Inferred proximity to restricted boundary [0, 1]")
    state_change_score: float = Field(0.0, ge=0.0, le=1.0, description="Inferred state change magnitude [0, 1]")
    behavioral_persistence: float = Field(0.0, ge=0.0, le=1.0, description="Persistence of probing behavior [0, 1]")
    accumulated_trajectory_risk: float = Field(0.0, ge=0.0, le=100.0, description="Accumulated trajectory risk R_t [0, 100]")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    explanation: str = Field(..., description="Explanatory rationale produced by detector")
    detector_name: str = Field(..., description="Detector identifier")
    detector_version: str = Field(..., description="Detector semantic version")


class TrajectoryPrediction(BaseModel):
    """Aggregated prediction for an entire agent trajectory."""
    trajectory_id: str = Field(..., description="Unique trajectory evaluated")
    detector_name: str = Field(..., description="Detector identifier")
    detector_version: str = Field(..., description="Detector semantic version")
    predicted_class: PredictedClass = Field(..., description="Overall predicted trajectory class")
    first_alert_step: Optional[int] = Field(None, description="Step index of first detection alert, if any")
    is_flagged: bool = Field(..., description="Whether trajectory was flagged as containing breach/hazard")
    max_risk_score: float = Field(0.0, ge=0.0, le=100.0, description="Peak risk score recorded")
    step_predictions: List[StepPrediction] = Field(default_factory=list, description="Per-step verdicts")
    execution_time_ms: float = Field(0.0, ge=0.0, description="Total execution latency in milliseconds")
    tokens_used: int = Field(0, ge=0, description="Tokens consumed during inference")
