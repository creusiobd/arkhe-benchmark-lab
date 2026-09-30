"""
ARKHÉ Agent Boundary Defense Benchmark — Observable Runtime Contract
====================================================================
Contains STRICTLY observable runtime signals available to detectors in production.

ZERO LABEL LEAKAGE GUARANTEE:
- NO ground truth labels (benign, near_violation, violation).
- NO attack vector identifiers.
- NO precomputed mission divergence scores.
- NO precomputed context contamination flags.
- NO precomputed risk scores.
- NO human evaluators' rationales or breach indices.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, model_validator


class ActionType(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    EXECUTE = "EXECUTE"
    NETWORK = "NETWORK"
    IPC = "IPC"
    TOOL_DISCOVERY = "TOOL_DISCOVERY"
    USER_INTERACTION = "USER_INTERACTION"


class BoundaryType(str, Enum):
    INDIRECT_PROMPT_INJECTION = "INDIRECT_PROMPT_INJECTION"
    TOOL_SCOPE_EXPANSION = "TOOL_SCOPE_EXPANSION"
    SECRET_EXPOSURE = "SECRET_EXPOSURE"
    UNAUTHORIZED_EXTERNAL_COMMUNICATION = "UNAUTHORIZED_EXTERNAL_COMMUNICATION"
    HUMAN_INTERVENTION_BYPASS_OR_CONCEALMENT = "HUMAN_INTERVENTION_BYPASS_OR_CONCEALMENT"


class AgentIdentity(BaseModel):
    agent_id: str = Field(..., description="Unique agent runtime identifier")
    role: str = Field(..., description="Declared role of agent")
    parent_agent_id: Optional[str] = Field(None, description="Parent agent ID in multi-agent graph")
    trust_tier: str = Field("INTERNAL_RESTRICTED", description="Trust level: UNTRUSTED, INTERNAL_RESTRICTED, ELEVATED")


class AgentMission(BaseModel):
    original_mission: str = Field(..., description="Original goal declared by user or supervisor")
    current_instruction: str = Field(..., description="Current observed active instruction at step")
    allowed_scope: List[str] = Field(default_factory=list, description="Declared allowed topics, directories or resources")


class ToolInvocation(BaseModel):
    tool_name: str = Field(..., description="Name of tool called")
    action_type: ActionType = Field(..., description="Type of operation")
    target_resource: str = Field(..., description="Target URI, path, domain, or memory slot")
    parameters_summary: Dict[str, Any] = Field(default_factory=dict, description="Sanitized parameters dictionary")


class CapabilityScope(BaseModel):
    allowed_tools: List[str] = Field(default_factory=list, description="Whitelist of tools available to agent")
    allowed_paths: List[str] = Field(default_factory=list, description="Allowed filesystem paths")
    allowed_hosts: List[str] = Field(default_factory=list, description="Allowed network domains/IPs")
    can_execute_code: bool = Field(False, description="Whether execution of arbitrary code is permitted")


class BoundaryPolicy(BaseModel):
    boundary_id: str = Field(..., description="Identifier of security boundary policy")
    boundary_type: str = Field(..., description="Defensive boundary family")
    description: str = Field(..., description="Policy description")
    forbidden_targets: List[str] = Field(default_factory=list, description="Explicitly forbidden target patterns")


class ExecutionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    WARNED = "WARNED"
    CONTAINED = "CONTAINED"
    DENIED = "DENIED"

    @property
    def is_containment_signal(self) -> bool:
        return self in (
            ExecutionStatus.BLOCKED,
            ExecutionStatus.WARNED,
            ExecutionStatus.CONTAINED,
            ExecutionStatus.DENIED,
        )

    @classmethod
    def is_containment(cls, val: Any) -> bool:
        s = str(getattr(val, "value", val) or "").strip().upper()
        return s in {"BLOCKED", "WARNED", "CONTAINED", "DENIED", "RESTRICTED"}


class ToolExecutionResult(BaseModel):
    status: str = Field(..., description="Execution status returned by tool environment: SUCCESS, BLOCKED, FAILED, WARNED, CONTAINED, DENIED")
    raw_observation: str = Field(..., description="Raw text observation returned by tool")

    @property
    def is_containment_signal(self) -> bool:
        return ExecutionStatus.is_containment(self.status)


class StepObservation(BaseModel):
    """
    Single execution step containing strictly observable runtime signals.
    Detectors receive this and MUST infer divergence, risk, and contamination dynamically.
    """
    trajectory_id: str = Field(..., description="Trajectory identifier")
    step_id: str = Field(..., description="Unique step identifier")
    step_index: int = Field(..., ge=0, description="Sequential index of step")
    logical_order: int = Field(..., ge=0, description="Logical ordering clock")
    timestamp_iso: Optional[str] = Field(None, description="ISO timestamp of observation")
    identity: AgentIdentity
    mission: AgentMission
    action: ToolInvocation
    capability: CapabilityScope
    boundary: BoundaryPolicy
    result: ToolExecutionResult

    @model_validator(mode="before")
    @classmethod
    def check_no_label_leakage(cls, data: Any) -> Any:
        assert_no_label_leakage(data, context_path="StepObservation")
        return data


FORBIDDEN_LEAKAGE_KEYS = {
    "ground_truth_label",
    "label",
    "ground_truth_class",
    "is_attack",
    "attack_vector",
    "attack_category",
    "violation_step_index",
    "drift_step_index",
    "breach_step",
    "drift_step",
    "mission_divergence_score",
    "context_contamination_flag",
    "accumulated_risk_score",
    "human_annotation_rationale",
    "evaluator_rationale",
    "expected_alert",
    "severity",
}


def assert_no_label_leakage(data: Any, context_path: str = "") -> None:
    """Recursively validates that no ground truth or precalculated risk leakage exists."""
    if isinstance(data, dict):
        found = FORBIDDEN_LEAKAGE_KEYS.intersection(data.keys())
        if found:
            raise ValueError(f"Label leakage detected at '{context_path}'! Forbidden fields present: {found}")
        for k, v in data.items():
            assert_no_label_leakage(v, f"{context_path}.{k}" if context_path else str(k))
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            assert_no_label_leakage(item, f"{context_path}[{idx}]")


class TrajectoryObservation(BaseModel):
    """Sequence of observable steps for a single agent trajectory."""
    trajectory_id: str = Field(..., description="Unique trajectory identifier")
    steps: List[StepObservation] = Field(default_factory=list, description="Ordered observable steps")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Safe metadata (e.g. environment type)")

    @model_validator(mode="before")
    @classmethod
    def check_trajectory_leakage(cls, data: Any) -> Any:
        assert_no_label_leakage(data, context_path="TrajectoryObservation")
        return data

    def to_sanitized_opaque(self) -> "TrajectoryObservation":
        """
        Produces an opaque copy where trajectory_id and step trajectory_ids are hashed to
        remove any semantic hints (e.g., BEN, NEA, VIO), and metadata is sanitized.
        """
        import hashlib
        opaque_id = f"traj_{hashlib.sha256(self.trajectory_id.encode('utf-8')).hexdigest()[:16]}"
        sanitized_steps = []
        for s in self.steps:
            s_dict = s.model_dump()
            s_dict["trajectory_id"] = opaque_id
            sanitized_steps.append(StepObservation.model_validate(s_dict))
        safe_meta = {k: v for k, v in self.metadata.items() if k in {"synthetic", "environment", "version"}}
        return TrajectoryObservation(
            trajectory_id=opaque_id,
            steps=sanitized_steps,
            metadata=safe_meta
        )
