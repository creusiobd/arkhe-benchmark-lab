"""Versioned defensive events. RuntimeContext is supplied by a trusted host.

Constructing a context is not authentication; the host must authenticate its
producer and derive tenant, principal and scopes outside the observed payload.
"""
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Annotated, Any, Literal, Union
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, TypeAdapter, field_validator, model_validator

Identifier = Annotated[StrictStr, Field(min_length=1, max_length=256,
    pattern=r'^[^\x00-\x1f\x7f]+$')]
FORBIDDEN_KEYS = frozenset({'ground_truth', 'ground_truth_label', 'ground_truth_class',
    'label', 'is_attack', 'attack_vector', 'violation_step_index', 'drift_step_index',
    'human_annotation_rationale', 'evaluator_rationale', 'mission_divergence_score',
    'context_contamination_flag', 'accumulated_risk_score'})

def reject_evaluation_fields(value: Any) -> Any:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in FORBIDDEN_KEYS:
                raise ValueError(f'evaluation field prohibited: {key}')
            reject_evaluation_fields(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            reject_evaluation_fields(nested)
    return value

def utc_datetime(value: Any) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('timezone-aware datetime required')
    return value.astimezone(timezone.utc)

class FrozenModel(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, validate_default=True,
                              revalidate_instances='always')

def json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    if isinstance(value, list):
        for child in value:
            json_value(child)
        return value
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        for child in value.values():
            json_value(child)
        return value
    raise ValueError('sanitized parameters/effects must contain finite JSON values')

class Authority(str, Enum):
    AGENT = 'agent'
    EXECUTOR = 'executor'
    SUPERVISOR = 'supervisor'
    POLICY_ADMIN = 'policy_admin'
    APPROVER = 'approver'

class RuntimeContext(FrozenModel):
    tenant_id: Identifier
    principal_id: Identifier
    producer_id: Identifier
    authority: Authority
    scopes: frozenset[Identifier] = frozenset()

class ActionType(str, Enum):
    READ = 'read'
    WRITE = 'write'
    EXECUTE = 'execute'
    NETWORK = 'network'
    IPC = 'ipc'
    TOOL_DISCOVERY = 'tool_discovery'
    USER_INTERACTION = 'user_interaction'

class CompletionStatus(str, Enum):
    SUCCESS = 'success'
    BLOCKED = 'blocked'
    FAILED = 'failed'

class EventEnvelope(FrozenModel):
    schema_version: Literal['1'] = '1'
    event_id: Identifier
    tenant_id: Identifier
    trajectory_id: Identifier
    agent_id: Identifier
    occurred_at: datetime
    ingested_at: datetime
    producer_id: Identifier
    correlation_id: Identifier | None = None
    parent_event_ids: tuple[Identifier, ...] = ()

    @field_validator('occurred_at', 'ingested_at', mode='before')
    @classmethod
    def aware(cls, value):
        return utc_datetime(value)

    @model_validator(mode='before')
    @classmethod
    def no_labels(cls, value):
        return reject_evaluation_fields(value)

    @model_validator(mode='after')
    def unique_parents(self):
        if len(set(self.parent_event_ids)) != len(self.parent_event_ids):
            raise ValueError('duplicate parent event IDs')
        if self.event_id in self.parent_event_ids:
            raise ValueError('event cannot be its own predecessor')
        return self

class ActionProposed(EventEnvelope):
    event_type: Literal['action_proposed'] = 'action_proposed'
    action_id: Identifier
    tool_name: Identifier
    action_type: ActionType
    target_resource: Annotated[StrictStr, Field(min_length=1, max_length=4096)]
    parameters_summary: dict[StrictStr, Any] = Field(default_factory=dict)
    policy_version: Identifier

    @field_validator('parameters_summary', mode='before')
    @classmethod
    def finite_json(cls, value):
        return json_value(value)

class ActionCompleted(EventEnvelope):
    event_type: Literal['action_completed'] = 'action_completed'
    action_id: Identifier
    proposal_event_id: Identifier
    status: CompletionStatus
    effects_summary: dict[StrictStr, Any] = Field(default_factory=dict)

    @field_validator('effects_summary', mode='before')
    @classmethod
    def finite_json(cls, value):
        return json_value(value)

class ApprovalRecorded(EventEnvelope):
    event_type: Literal['approval_recorded'] = 'approval_recorded'
    approval_id: Identifier
    action_id: Identifier
    action_hash: Annotated[StrictStr, Field(pattern=r'^[0-9a-f]{64}$')]
    policy_version: Identifier
    expires_at: datetime
    revocation_of: Identifier | None = None

    @field_validator('expires_at', mode='before')
    @classmethod
    def expiry_aware(cls, value):
        return utc_datetime(value)

    @model_validator(mode='after')
    def expiry_order(self):
        if self.expires_at <= self.occurred_at:
            raise ValueError('approval expiry must follow issue time')
        return self

class PolicyChanged(EventEnvelope):
    event_type: Literal['policy_changed'] = 'policy_changed'
    policy_version: Identifier
    policy_hash: Annotated[StrictStr, Field(pattern=r'^[0-9a-f]{64}$')]

class TrajectoryClosed(EventEnvelope):
    event_type: Literal['trajectory_closed'] = 'trajectory_closed'
    reason: Annotated[StrictStr, Field(min_length=1, max_length=1024)]

Event = Annotated[Union[ActionProposed, ActionCompleted, ApprovalRecorded,
    PolicyChanged, TrajectoryClosed], Field(discriminator='event_type')]
EVENT_ADAPTER = TypeAdapter(Event)

def parse_event(payload: Any) -> Event:
    if isinstance(payload, BaseModel):
        payload = payload.model_dump(mode='python')
    if isinstance(payload, (str, bytes, bytearray)):
        return EVENT_ADAPTER.validate_json(payload)
    return EVENT_ADAPTER.validate_python(payload)

class DecisionStatus(str, Enum):
    WITHIN_POLICY = 'within_policy'
    APPROVAL_REQUIRED = 'approval_required'
    POLICY_VIOLATION = 'policy_violation'
    INSUFFICIENT_EVIDENCE = 'insufficient_evidence'

class Decision(FrozenModel):
    decision_id: Identifier
    event_id: Identifier
    tenant_id: Identifier
    trajectory_id: Identifier
    status: DecisionStatus
    mode: Literal['observe'] = 'observe'
    policy_version: Identifier | None = None
    policy_hash: StrictStr | None = None
    rule_ids: tuple[Identifier, ...] = ()
    evidence_refs: tuple[Identifier, ...] = ()
    missing_fields: tuple[StrictStr, ...] = ()
    context_loss_reason: StrictStr | None = None
    revision: Annotated[StrictInt, Field(ge=0)] = 0
    has_observed_violation: StrictBool = False
    first_alert_event_id: Identifier | None = None
