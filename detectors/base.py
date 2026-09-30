"""
ARKHÉ Agent Boundary Defense Benchmark — Base Detector Interface
================================================================
Defines contract for defensive detectors.

ISOLATION GUARANTEE:
Detectors consume ONLY `StepObservation` and optional historical `List[StepObservation]`.
Ground truth classes and breach metadata are strictly absent.
"""

import time
from abc import ABC, abstractmethod
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from contracts.observation import StepObservation, TrajectoryObservation
from contracts.prediction import StepPrediction, TrajectoryPrediction, PredictedClass


def get_step_index(step: Any) -> int:
    return getattr(step, "step_index", getattr(getattr(step, "state", None), "step_index", 0))


def get_raw_observation(step: Any) -> str:
    res = getattr(step, "result", None) or getattr(step, "outcome", None)
    return getattr(res, "raw_observation", "") if res else ""


def get_outcome_status(step: Any) -> str:
    res = getattr(step, "result", None) or getattr(step, "outcome", None)
    return str(getattr(res, "status", "")) if res else ""


def is_containment_status(step: Any) -> bool:
    res = getattr(step, "result", None) or getattr(step, "outcome", None)
    if not res:
        return False
    if hasattr(res, "is_containment_signal"):
        return bool(res.is_containment_signal)
    status_str = str(getattr(res, "status", "")).strip().upper()
    return status_str in {"BLOCKED", "WARNED", "CONTAINED", "DENIED", "RESTRICTED"}


def get_mission_instruction(step: Any) -> str:
    mission = getattr(step, "mission", None)
    if not mission:
        return ""
    return getattr(mission, "current_instruction", getattr(mission, "current_mission", ""))


class BaseDetector(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique detector identifier."""
        pass

    @property
    def version(self) -> str:
        """Detector version string."""
        return "1.0.0"

    @property
    @abstractmethod
    def detection_mode(self) -> str:
        """ISOLATED_EVENT or TRAJECTORY_AWARE."""
        pass

    @abstractmethod
    def evaluate_step(
        self,
        step: StepObservation,
        trajectory_history: Optional[List[StepObservation]] = None
    ) -> StepPrediction:
        """Evaluates a single execution step using strictly observable data."""
        pass

    def evaluate_trajectory(self, trajectory: TrajectoryObservation) -> TrajectoryPrediction:
        """
        Executes step-by-step evaluation of an entire trajectory,
        accumulating observable history strictly up to the current step.
        """
        start_time = time.perf_counter()
        history: List[StepObservation] = []
        step_predictions: List[StepPrediction] = []
        first_alert_step: Optional[int] = None
        max_risk = 0.0

        for step in trajectory.steps:
            pred = self.evaluate_step(step, trajectory_history=list(history))
            step_predictions.append(pred)
            history.append(step)

            if pred.accumulated_trajectory_risk > max_risk:
                max_risk = pred.accumulated_trajectory_risk

            if pred.is_alert and first_alert_step is None:
                first_alert_step = pred.step_index

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        # Classify overall trajectory
        if self.detection_mode == "TRAJECTORY_AWARE":
            # Check for trajectory recovery (near violation that safely relaxed)
            is_recovered = any("TRAJECTORY RECOVERY" in p.explanation for p in step_predictions)
            is_flagged = (first_alert_step is not None) and not is_recovered
        else:
            is_flagged = first_alert_step is not None

        if is_flagged:
            predicted_class = PredictedClass.VIOLATION
        else:
            predicted_class = PredictedClass.BENIGN

        return TrajectoryPrediction(
            trajectory_id=trajectory.trajectory_id,
            detector_name=self.name,
            detector_version=self.version,
            predicted_class=predicted_class,
            first_alert_step=first_alert_step if is_flagged else None,
            is_flagged=is_flagged,
            max_risk_score=max_risk,
            step_predictions=step_predictions,
            execution_time_ms=duration_ms,
            tokens_used=0
        )


# Backward compatibility classes & aliases
BaseAgentDetector = BaseDetector


class DetectionVerdict(BaseModel):
    is_violation_suspected: bool = Field(..., description="Whether detector flags this step as an imminent or active breach")
    step_index: int = Field(..., description="Step index where verdict was issued")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    detection_type: str = Field(..., description="ISOLATED_EVENT or TRAJECTORY_AWARE")
    reasoning: str = Field(..., description="Explanatory rationale for the verdict")
    evidence: Optional[str] = Field(None, description="Auditable evidence extracted")
    risk_score: float = Field(0.0, ge=0.0, le=100.0, description="Estimated risk magnitude")


