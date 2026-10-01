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
from pydantic import BaseModel, Field, ConfigDict, model_validator


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


class AlertEmitted(BaseModel):
    """
    Immutable, append-only security alert event emitted by a detector at a specific step.
    Represents the fact that at step `step_index` (or timestamp), the detector observed
    anomalous risk exceeding its decision threshold.

    SEMANTIC IMMUTABILITY GUARANTEE:
    - Once instantiated, this event cannot be altered, erased, or retroactively modified (frozen=True).
    - Evidences and explanations reflect strictly the observable information available at the time of emission.
    """
    model_config = ConfigDict(frozen=True)

    event_type: str = Field("alert_emitted", description="Event type discriminator")
    schema_version: str = Field("1.0.0", description="Event schema version")
    alert_id: str = Field(..., description="Unique immutable alert event ID")
    trajectory_id: str = Field(..., description="Target opaque trajectory ID")
    detector_name: str = Field(..., description="Detector that emitted the alert")
    detector_version: str = Field("1.0.0", description="Detector semantic version")
    step_index: int = Field(..., ge=0, description="Step index where alert was emitted")
    timestamp: Optional[str] = Field(None, description="ISO timestamp of observation if available")
    risk_score: float = Field(..., ge=0.0, description="Risk score or Lyapunov energy at time of alert")
    threshold: float = Field(..., ge=0.0, description="Alert threshold applied")
    severity: AlertSeverity = Field(AlertSeverity.HIGH, description="Alert severity level")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Observable evidence available at emission step")
    explanation: str = Field("", description="Explanatory rationale produced strictly at the moment of emission")


class AlertResolved(BaseModel):
    """
    Immutable event indicating an alert condition was subsequently resolved or relaxed.
    Never mutates or deletes the original AlertEmitted event.
    """
    model_config = ConfigDict(frozen=True)

    event_type: str = Field("alert_resolved", description="Event type discriminator")
    schema_version: str = Field("1.0.0", description="Event schema version")
    event_id: str = Field(..., description="Unique immutable resolution event ID")
    resolution_id: Optional[str] = Field(None, description="Backwards-compatible alias for event_id")
    alert_id: Optional[str] = Field(None, description="ID of associated AlertEmitted event")
    trajectory_id: str = Field(..., description="Target opaque trajectory ID")
    step_index: int = Field(..., ge=0, description="Step index where resolution occurred")
    timestamp: Optional[str] = Field(None, description="ISO timestamp if available")
    resolution_reason: str = Field("NOMINAL_RECOVERY", description="Reason or mechanism of resolution")
    resolution_type: str = Field("NOMINAL_RECOVERY", description="Backwards-compatible alias for resolution_reason")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Observable evidence at resolution step")

    @model_validator(mode="before")
    @classmethod
    def _sync_ids_and_reasons(cls, data: Any) -> Any:
        if isinstance(data, dict):
            d = dict(data)
            if "resolution_id" in d and "event_id" not in d:
                d["event_id"] = d["resolution_id"]
            elif "event_id" in d and "resolution_id" not in d:
                d["resolution_id"] = d["event_id"]
            if "resolution_type" in d and "resolution_reason" not in d:
                d["resolution_reason"] = d["resolution_type"]
            elif "resolution_reason" in d and "resolution_type" not in d:
                d["resolution_type"] = d["resolution_reason"]
            return d
        return data


class ContainmentAttempted(BaseModel):
    """
    Immutable event recording an attempted containment action and its verifiable outcome.
    References the corresponding alert_id when available.
    
    IMPORTANT: containment_succeeded is NOT inferred merely because an agent retreated
    or relaxed; it must reflect explicit observable containment signals (e.g., BLOCKED,
    CONTAINED, or explicit enforcement).
    """
    model_config = ConfigDict(frozen=True)

    event_type: str = Field("containment_attempted", description="Event type discriminator")
    schema_version: str = Field("1.0.0", description="Event schema version")
    event_id: str = Field(..., description="Unique immutable containment event ID")
    containment_id: Optional[str] = Field(None, description="Backwards-compatible alias for event_id")
    alert_id: Optional[str] = Field(None, description="ID of associated AlertEmitted event")
    trajectory_id: str = Field(..., description="Target opaque trajectory ID")
    step_index: int = Field(..., ge=0, description="Step index where containment was observed/attempted")
    timestamp: Optional[str] = Field(None, description="ISO timestamp if available")
    containment_attempted: bool = Field(True, description="Whether containment was attempted")
    containment_succeeded: Optional[bool] = Field(None, description="Whether containment demonstrably succeeded")
    action_taken: str = Field(..., description="Containment action or signal observed")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Observable evidence at containment step")

    @model_validator(mode="before")
    @classmethod
    def _sync_containment_ids(cls, data: Any) -> Any:
        if isinstance(data, dict):
            d = dict(data)
            if "containment_id" in d and "event_id" not in d:
                d["event_id"] = d["containment_id"]
            elif "event_id" in d and "containment_id" not in d:
                d["containment_id"] = d["event_id"]
            return d
        return data


# Backward-compatible class aliases
AlertEvent = AlertEmitted
ResolutionEvent = AlertResolved
ContainmentEvent = ContainmentAttempted


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
    alerts: List[AlertEmitted] = Field(default_factory=list, description="Immutable append-only alerts emitted during trajectory")
    resolutions: List[AlertResolved] = Field(default_factory=list, description="Resolution events recorded")
    containments: List[ContainmentAttempted] = Field(default_factory=list, description="Containment events recorded")
    final_outcome: Optional[str] = Field(None, description="Final trajectory outcome (FinalOutcome enum value)")
    total_alerts_emitted: int = Field(0, ge=0, description="Total count of alert events emitted")
    total_alerts_resolved: int = Field(0, ge=0, description="Total count of resolution events recorded")
