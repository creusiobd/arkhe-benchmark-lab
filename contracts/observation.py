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


class ToolExecutionResult(BaseModel):
    status: str = Field(..., description="Execution status returned by tool environment: SUCCESS, BLOCKED, FAILED, WARNED")
    raw_observation: str = Field(..., description="Raw text observation returned by tool")


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
        if isinstance(data, dict):
            forbidden_keys = {
                "ground_truth_label",
                "label",
                "ground_truth_class",
                "is_attack",
                "attack_vector",
                "violation_step_index",
                "drift_step_index",
                "mission_divergence_score",
                "context_contamination_flag",
                "accumulated_risk_score",
                "human_annotation_rationale",
                "evaluator_rationale",
            }
            found = forbidden_keys.intersection(data.keys())
            if found:
                raise ValueError(f"Label leakage detected! Forbidden fields present in observation: {found}")
        return data


class TrajectoryObservation(BaseModel):
    """Sequence of observable steps for a single agent trajectory."""
    trajectory_id: str = Field(..., description="Unique trajectory identifier")
    steps: List[StepObservation] = Field(default_factory=list, description="Ordered observable steps")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Safe metadata (e.g. environment type)")
