"""Infrastructure-independent observable contracts; no defense-agent imports."""
from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from math import isfinite
from types import MappingProxyType
from typing import Mapping
from .errors import EventValidationError


def identifier(value, path, error=EventValidationError):
    if (not isinstance(value, str) or not value.strip() or len(value) > 256
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise error(f'{path}: nonempty identifier without control characters required (max 256)')


def finite(value):
    try:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)
    except (OverflowError, TypeError):
        return False


def aware(value, path):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise EventValidationError(f'{path}: timezone-aware datetime required')
    return value.astimezone(timezone.utc)


def timestamp(value, path):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError as exc:
            raise EventValidationError(f'{path}: invalid ISO timestamp') from exc
    return aware(value, path)


def json_value(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, '__dataclass_fields__'):
        return {f.name: json_value(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, Mapping):
        return {key: json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_value(item) for item in value]
    return value


@dataclass(frozen=True)
class TrajectoryEvent:
    tenant_id: str
    journey_id: str
    journey_version: str
    trajectory_id: str
    event_id: str
    step_id: str
    event_time: datetime
    ingested_at: datetime
    metrics: Mapping[str, float]
    dimensions: Mapping[str, str | int | float | bool] = field(default_factory=dict)
    outcome: str | None = None
    schema_version: str = '1'

    def __post_init__(self):
        if self.schema_version != '1':
            raise EventValidationError('schema_version: only 1 supported')
        for name in ('tenant_id', 'journey_id', 'journey_version', 'trajectory_id', 'event_id', 'step_id'):
            identifier(getattr(self, name), name)
        for name in ('event_time', 'ingested_at'):
            object.__setattr__(self, name, aware(getattr(self, name), name))
        if self.ingested_at < self.event_time:
            raise EventValidationError('ingested_at: cannot precede event_time')
        if not isinstance(self.metrics, Mapping) or len(self.metrics) > 128:
            raise EventValidationError('metrics: mapping with at most 128 entries required')
        for key, value in self.metrics.items():
            identifier(key, 'metrics.key')
            if not finite(value):
                raise EventValidationError('metrics: finite numeric value required')
        if not isinstance(self.dimensions, Mapping) or len(self.dimensions) > 32:
            raise EventValidationError('dimensions: mapping with at most 32 entries required')
        for key, value in self.dimensions.items():
            identifier(key, 'dimensions.key')
            if (not isinstance(value, (str, int, float, bool)) or
                    isinstance(value, (int, float)) and not isinstance(value, bool) and not finite(value)):
                raise EventValidationError('dimensions: finite scalar required')
            if isinstance(value, str) and len(value) > 1024:
                raise EventValidationError('dimensions: maximum 1024 characters per value')
        if self.outcome is not None:
            identifier(self.outcome, 'outcome')
        object.__setattr__(self, 'metrics', MappingProxyType(dict(self.metrics)))
        object.__setattr__(self, 'dimensions', MappingProxyType(dict(self.dimensions)))

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, Mapping):
            raise EventValidationError('event: object required')
        names = {f.name for f in fields(cls)}
        if set(data) - names:
            raise EventValidationError('event: unknown fields')
        values = dict(data)
        for name in ('event_time', 'ingested_at'):
            if name in values:
                values[name] = timestamp(values[name], name)
        try:
            return cls(**values)
        except TypeError as exc:
            raise EventValidationError('event: missing or invalid fields') from exc

    def to_dict(self):
        return json_value(self)


Event = TrajectoryEvent


@dataclass(frozen=True)
class RuleFinding:
    rule_id: str
    metric: str
    observed: float | None
    baseline: float | None
    threshold: float
    reason: str
    severity: str = 'warning'
    evidence_event_ids: tuple[str, ...] = ()
    aggregation: str = 'latest'
    reference: str = 'absolute'
    comparison_value: float | None = None
    sample_count: int = 0
    elapsed_seconds: float | None = None
    evidence_truncated: bool = False


@dataclass(frozen=True)
class TrajectoryAssessment:
    tenant_id: str
    journey_id: str
    journey_version: str
    trajectory_id: str
    status: str
    evaluated_at: datetime
    findings: tuple[RuleFinding, ...] = ()
    trends: Mapping[str, float] = field(default_factory=dict)
    missing_expected_steps: tuple[str, ...] = ()
    context_loss_reason: str | None = None
    missing_metrics: tuple[str, ...] = ()
    configuration_hash: str | None = None
    window_end: datetime | None = None
    total_findings: int = 0
    findings_truncated: bool = False

    def __post_init__(self):
        if self.status not in ('normal', 'deviation', 'insufficient_evidence'):
            raise EventValidationError('status: invalid assessment status')
        aware(self.evaluated_at, 'evaluated_at')
        for name in ('findings', 'missing_expected_steps', 'missing_metrics'):
            object.__setattr__(self, name, tuple(getattr(self, name)))
        object.__setattr__(self, 'trends', MappingProxyType(dict(self.trends)))

    def to_dict(self):
        return json_value(self)
