"""
ARKHÉ Agent Boundary Defense Benchmark — Canonical Schema
=========================================================
Strict two-layer schema eliminating label leakage:
1. Observable Layer: Data available to detectors at runtime (Identity, Mission text,
   Action, Capability, Boundary constraints, raw observations).
2. Ground Truth Layer: Reserved exclusively for evaluation (Labels, attack vector,
   human rationale, violation step index).

Detectors MUST calculate divergence, risk, and contamination internally.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ActionType(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    EXECUTE = "EXECUTE"
    NETWORK = "NETWORK"
    IPC = "IPC"
    TOOL_DISCOVERY = "TOOL_DISCOVERY"
    USER_INTERACTION = "USER_INTERACTION"


class BoundaryType(str, Enum):
    PROMPT_INJECTION_PROPAGATION = "PROMPT_INJECTION_PROPAGATION"
    TOOL_SCOPE_EXPANSION = "TOOL_SCOPE_EXPANSION"
    SECRET_EXPOSURE = "SECRET_EXPOSURE"
    UNAUTHORIZED_EXTERNAL_COMMUNICATION = "UNAUTHORIZED_EXTERNAL_COMMUNICATION"
    HUMAN_INTERVENTION_BYPASS_OR_MISSION_HIJACK = "HUMAN_INTERVENTION_BYPASS_OR_MISSION_HIJACK"


class TrajectoryLabel(str, Enum):
    BENIGN = "BENIGN"
    NEAR_VIOLATION = "NEAR_VIOLATION"
    VIOLATION = "VIOLATION"


class StepOutcomeStatus(str, Enum):
    SUCCESS = "SUCCESS"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    WARNED = "WARNED"


# ==============================================================================
# CAMADA 1: DADOS OBSERVÁVEIS PELO DETECTOR (OBSERVABLE RUNTIME LAYER)
# NENHUM rótulo, flag de contaminação pré-calculada ou score de risco aqui.
# ==============================================================================

class AgentIdentity(BaseModel):
    agent_id: str = Field(..., description="Unique identifier for the agent instance")
    role: str = Field(..., description="Declared role of agent")
    parent_agent_id: Optional[str] = Field(None, description="Parent agent ID in multi-agent hierarchy")
    trust_tier: str = Field("INTERNAL_RESTRICTED", description="Trust level: UNTRUSTED, INTERNAL_RESTRICTED, ELEVATED")


class ObservableMission(BaseModel):
    original_mission: str = Field(..., description="Original goal declared by user or supervisor")
    current_mission: str = Field(..., description="Current mission text declared/inferred at step")
    allowed_scope: List[str] = Field(default_factory=list, description="Declared allowed topics or resources")


class ToolAction(BaseModel):
    tool_name: str = Field(..., description="Name of tool called")
    action_type: ActionType = Field(..., description="Type of operation")
    target_resource: str = Field(..., description="Target URI, path, domain, or memory slot")
    parameters_summary: Dict[str, Any] = Field(default_factory=dict, description="Sanitized parameters dictionary")


class CapabilityScope(BaseModel):
    allowed_tools: List[str] = Field(default_factory=list, description="Whitelist of tools available to agent")
    allowed_paths: List[str] = Field(default_factory=list, description="Allowed filesystem paths")
    allowed_hosts: List[str] = Field(default_factory=list, description="Allowed network domains/IPs")
    can_execute_code: bool = Field(False, description="Whether execution of arbitrary code is permitted")


class BoundaryConstraint(BaseModel):
    boundary_id: str = Field(..., description="Identifier of security boundary")
    boundary_type: BoundaryType = Field(..., description="Family of the defensive boundary")
    description: str = Field(..., description="Human-readable constraint description")
    forbidden_targets: List[str] = Field(default_factory=list, description="Explicitly forbidden target patterns")


class ObservableState(BaseModel):
    step_index: int = Field(..., ge=0, description="Sequential index of the execution step")


class ObservableOutcome(BaseModel):
    status: StepOutcomeStatus = Field(..., description="Execution status returned to agent")
    raw_observation: str = Field(..., description="Raw text observation returned by tool")


class ObservableStep(BaseModel):
    """Single execution step containing strictly observable runtime signals."""
    step_id: str = Field(..., description="Unique step identifier")
    identity: AgentIdentity
    mission: ObservableMission
    action: ToolAction
    capability: CapabilityScope
    boundary: BoundaryConstraint
    state: ObservableState
    outcome: ObservableOutcome


# ==============================================================================
# CAMADA 2: GROUND TRUTH RESERVADO À AVALIAÇÃO (EVALUATION GROUND TRUTH LAYER)
# Nunca fornecido como entrada aos detectores. Usado apenas pelo harness avaliador.
# ==============================================================================

class TrajectoryGroundTruth(BaseModel):
    ground_truth_label: TrajectoryLabel = Field(..., description="True trajectory classification")
    violation_step_index: Optional[int] = Field(None, description="Step index where explicit breach occurred")
    drift_step_index: Optional[int] = Field(None, description="Step index where initial mission drift began")
    violating_boundary_id: Optional[str] = Field(None, description="ID of boundary breached")
    attack_vector: Optional[str] = Field(None, description="Attack classification (e.g. INDIRECT_PROMPT_INJECTION)")
    human_annotation_rationale: str = Field(..., description="Auditable rationale written by security annotator")


class AgentTrajectory(BaseModel):
    """Complete trajectory bundle pairing observable data with evaluation ground truth."""
    trajectory_id: str = Field(..., description="Unique trajectory identifier")
    scenario_family: BoundaryType
    observable_steps: List[ObservableStep] = Field(default_factory=list, description="Inputs for detectors")
    ground_truth: TrajectoryGroundTruth = Field(..., description="Hidden labels for evaluation only")
    metadata: Dict[str, Any] = Field(default_factory=dict)
