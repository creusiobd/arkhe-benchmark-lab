"""
ARKHÉ Agent Boundary Defense Benchmark — Prediction and Event Contracts
========================================================================
Defines the output produced by defensive detectors when evaluating observable steps,
including immutable append-only alert events, resolution events, containment tracking,
and overall trajectory predictions.

SEMANTIC IMMUTABILITY GUARANTEE:
- Alerts once emitted are append-only and immutable.
- Subsequent trajectory recovery generates a ResolutionEvent, but NEVER erases,
  resets, or mutates previously emitted alerts or flags.
- Containment is tracked as a distinct event and is never inferred solely from recovery.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class PredictedClass(str, Enum):
    BENIGN = "benign"
    NEAR_VIOLATION = "near_violation"
    VIOLATION = "violation"


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FinalOutcome(str, Enum):
    """Final trajectory lifecycle outcome."""
    NOMINAL_EXECUTION = "nominal_execution"
    RECOVERED_AFTER_ALERT = "recovered_after_alert"
    UNRESOLVED_ALERT = "unresolved_alert"
    VIOLATION_CONSUMMATED = "violation_consummated"


class AlertEvent(BaseModel):
    """
    Immutable, append-only security alert event emitted by a detector at a specific step.
    Represents the fact that at step `step_index` (or timestamp), the detector observed
    anomalous risk exceeding its decision threshold.
    """
    alert_id: str = Field(..., description="Unique immutable alert event ID")
    trajectory_id: str = Field(..., description="Target trajectory ID")
    detector_name: str = Field(..., description="Detector that emitted the alert")
    detector_version: str = Field(..., description="Detector semantic version")
    step_index: int = Field(..., ge=0, description="Step index where alert was emitted")
    timestamp: Optional[str] = Field(None, description="ISO timestamp of observation if available")
    risk_score: float = Field(..., description="Risk score or Lyapunov energy at time of alert")
    threshold: float = Field(..., description="Alert threshold applied")
    severity: AlertSeverity = Field(AlertSeverity.HIGH, description="Alert severity level")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Observable evidence available at emission step")


class ResolutionEvent(BaseModel):
    """
    Immutable event indicating an alert condition was subsequently resolved or relaxed.
    Never mutates or deletes the original AlertEvent.
    """
    resolution_id: str = Field(..., description="Unique resolution event ID")
    alert_id: Optional[str] = Field(None, description="ID of associated alert event, if specific")
    trajectory_id: str = Field(..., description="Target trajectory ID")
    step_index: int = Field(..., ge=0, description="Step index where resolution occurred")
    timestamp: Optional[str] = Field(None, description="ISO timestamp if available")
    resolution_type: str = Field("NOMINAL_RECOVERY", description="Type of resolution (e.g. NOMINAL_RECOVERY, RISK_SUBSIDED)")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Observable evidence at resolution step")


class ContainmentEvent(BaseModel):
    """
    Event recording an attempted containment action and its verifiable outcome.
    
    IMPORTANT: containment_succeeded is NOT inferred merely because an agent retreated
    or relaxed; it must reflect explicit observable containment signals (e.g., BLOCKED,
    CONTAINED, or explicit enforcement).
    """
    containment_id: str = Field(..., description="Unique containment event ID")
    trajectory_id: str = Field(..., description="Target trajectory ID")
    step_index: int = Field(..., ge=0, description="Step index where containment was observed/attempted")
    timestamp: Optional[str] = Field(None, description="ISO timestamp if available")
    containment_attempted: bool = Field(True, description="Whether containment was attempted")
    containment_succeeded: Optional[bool] = Field(None, description="Whether containment demonstrably succeeded")
    action_taken: str = Field(..., description="Containment action or signal observed")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Observable evidence at containment step")


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
    
    # Immutable event lifecycle
    alerts: List[AlertEvent] = Field(default_factory=list, description="Immutable append-only alerts emitted during trajectory")
    resolutions: List[ResolutionEvent] = Field(default_factory=list, description="Resolution events recorded")
    containments: List[ContainmentEvent] = Field(default_factory=list, description="Containment events recorded")
    final_outcome: Optional[str] = Field(None, description="Final trajectory outcome (FinalOutcome enum value)")
    total_alerts_emitted: int = Field(0, ge=0, description="Total count of alert events emitted")
    total_alerts_resolved: int = Field(0, ge=0, description="Total count of resolution events recorded")
