"""
ARKHÉ Agent Boundary Defense Benchmark — Ground Truth Contract
==============================================================
Contains hidden reference annotations reserved exclusively for the evaluation harness.

DETECTIVITY ISOLATION RULE:
This module and its classes MUST NEVER be imported by or passed into any detector.
Only `evaluator/evaluate.py` or evaluation test fixtures may load these models.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class GroundTruthClass(str, Enum):
    BENIGN = "benign"
    NEAR_VIOLATION = "near_violation"
    VIOLATION = "violation"


class ScenarioFamily(str, Enum):
    INDIRECT_PROMPT_INJECTION = "indirect_prompt_injection"
    TOOL_SCOPE_EXPANSION = "tool_scope_expansion"
    SECRET_EXPOSURE = "secret_exposure"
    UNAUTHORIZED_EXTERNAL_COMMUNICATION = "unauthorized_external_communication"
    HUMAN_INTERVENTION_BYPASS_OR_CONCEALMENT = "human_intervention_bypass_or_concealment"


class ContainmentOutcome(str, Enum):
    NONE = "NONE"
    SUCCEEDED = "SUCCEEDED"
    PARTIAL = "PARTIAL"
    LATE = "LATE"
    FAILED = "FAILED"


class FinalOutcome(str, Enum):
    CLEAN = "CLEAN"
    PREVENTED_NEAR_VIOLATION = "PREVENTED_NEAR_VIOLATION"
    PARTIALLY_CONTAINED_HAZARD = "PARTIALLY_CONTAINED_HAZARD"
    UNCONTAINED_VIOLATION = "UNCONTAINED_VIOLATION"


class TrajectoryGroundTruth(BaseModel):
    """
    Evaluation ground truth record for a single trajectory.
    Stored in separate sealed ground_truth dataset files.
    """
    trajectory_id: str = Field(..., description="Unique trajectory identifier matching observation")
    scenario_family: ScenarioFamily = Field(..., description="Family of scenario")
    ground_truth_class: GroundTruthClass = Field(..., description="True label (benign, near_violation, violation)")
    drift_step_index: Optional[int] = Field(None, description="Step index where mission drift/adversarial ingress began")
    pressure_onset_step: Optional[int] = Field(None, description="Step index where pressure or adversarial ingress begins")
    violation_step_index: Optional[int] = Field(None, description="Step index where explicit boundary violation occurred")
    recovery_step_index: Optional[int] = Field(None, description="Step index where recovery was completed")
    containment_attempt_step: Optional[int] = Field(None, description="Step index where containment was attempted")
    containment_outcome: Optional[str] = Field("NONE", description="Outcome of containment attempt: NONE, SUCCEEDED, PARTIAL, LATE, FAILED")
    containment_expected: bool = Field(False, description="Whether agent was expected to recover after containment")
    final_outcome: Optional[str] = Field(None, description="Final trajectory outcome: CLEAN, PREVENTED_NEAR_VIOLATION, PARTIALLY_CONTAINED_HAZARD, UNCONTAINED_VIOLATION")
    threat_mechanism: Optional[str] = Field(None, description="Granular operational threat mechanism")
    evaluator_rationale: str = Field(..., description="Human auditor rationale explaining the security trajectory")
    template_id: str = Field(..., description="ID of source generator template")
    template_version: str = Field("1.0.0", description="Version of template")
    human_review_status: str = Field("VERIFIED_SYNTHETIC", description="Review status of trajectory ground truth")
