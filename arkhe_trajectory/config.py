"""Explicit versioned customer journey configuration, without inferred defaults."""
from dataclasses import dataclass, fields
from types import MappingProxyType
from typing import Mapping
from .contracts import identifier, finite
from .errors import ConfigurationError

def strict(cls, data):
    if not isinstance(data, Mapping):
        raise ConfigurationError(f'{cls.__name__}: object required')
    unknown = set(data) - {f.name for f in fields(cls)}
    if unknown:
        raise ConfigurationError(f'{cls.__name__}: unknown fields {sorted(unknown)}')
    try:
        return cls(**data)
    except TypeError as exc:
        raise ConfigurationError(f'{cls.__name__}: missing or invalid fields') from exc

def positive(value, name, zero=False):
    if not finite(value) or value < 0 or value > 31536000 or (not zero and value == 0):
        raise ConfigurationError(f'{name}: finite {"nonnegative" if zero else "positive"} number required (maximum 31536000 seconds)')

@dataclass(frozen=True)
class JourneyStep:
    step_id: str
    expected_next: tuple[str, ...] = ()
    max_delay_seconds: float | None = None

    def __post_init__(self):
        identifier(self.step_id,'steps.step_id',ConfigurationError)
        if not isinstance(self.expected_next,(list,tuple)):
            raise ConfigurationError('steps.expected_next: array required')
        for target in self.expected_next:
            identifier(target,'steps.expected_next',ConfigurationError)
        if len(set(self.expected_next)) != len(self.expected_next):
            raise ConfigurationError('steps.expected_next: duplicate targets')
        object.__setattr__(self,'expected_next',tuple(self.expected_next))
        if self.max_delay_seconds is not None:
            positive(self.max_delay_seconds,'steps.max_delay_seconds')
            if not self.expected_next:
                raise ConfigurationError('steps.max_delay_seconds: expected_next required')

@dataclass(frozen=True)
class ThresholdRule:
    rule_id: str
    metric: str
    operator: str
    threshold: float
    severity: str = 'warning'
    aggregation: str = 'latest'
    step_id: str | None = None
    min_samples: int = 1
    persistence: int = 1
    reference: str = 'absolute'

    def __post_init__(self):
        identifier(self.rule_id,'rules.rule_id',ConfigurationError)
        identifier(self.metric,'rules.metric',ConfigurationError)
        if self.operator not in ('gt','ge','lt','le'):
            raise ConfigurationError('rules.operator: expected gt/ge/lt/le')
        if not finite(self.threshold):
            raise ConfigurationError('rules.threshold: finite numeric value required')
        if self.severity not in ('warning','critical'):
            raise ConfigurationError('rules.severity: expected warning/critical')
        if self.aggregation not in ('latest','mean','max','min','slope'):
            raise ConfigurationError('rules.aggregation: invalid aggregate')
        for name in ('min_samples','persistence'):
            value = getattr(self,name)
            if type(value) is not int or value < 1:
                raise ConfigurationError(f'rules.{name}: positive integer required')
        if self.aggregation == 'slope' and self.min_samples < 2:
            raise ConfigurationError('rules.min_samples: slope requires at least 2')
        if self.reference not in ('absolute','delta','relative'):
            raise ConfigurationError('rules.reference: expected absolute/delta/relative')
        if self.aggregation == 'slope' and self.reference != 'absolute':
            raise ConfigurationError('rules.reference: slope uses absolute metric/second units')
        if self.step_id is not None:
            identifier(self.step_id,'rules.step_id',ConfigurationError)

@dataclass(frozen=True)
class JourneyConfig:
    tenant_id: str
    journey_id: str
    version: str
    steps: tuple[JourneyStep, ...]
    window_seconds: float
    baseline: Mapping[str,float]
    rules: tuple[ThresholdRule, ...]
    ttl_seconds: float = 1800
    max_events: int = 10000
    max_trajectories: int = 1000
    max_lateness_seconds: float = 0
    max_payload_bytes: int = 65536
    max_evidence_refs: int = 32
    max_findings: int = 128
    schema_version: str = '1'

    def __post_init__(self):
        if self.schema_version != '1':
            raise ConfigurationError('schema_version: only 1 supported')
        for name in ('tenant_id','journey_id','version'):
            identifier(getattr(self,name),name,ConfigurationError)
        for name in ('steps','rules'):
            value = getattr(self,name)
            cls = JourneyStep if name == 'steps' else ThresholdRule
            if not isinstance(value,(list,tuple)) or not value or not all(isinstance(x,cls) for x in value):
                raise ConfigurationError(f'{name}: nonempty typed array required')
            if len(value) > 128:
                raise ConfigurationError(f'{name}: maximum 128 entries')
            object.__setattr__(self,name,tuple(value))
        ids = [s.step_id for s in self.steps]
        if len(ids) != len(set(ids)):
            raise ConfigurationError('steps: duplicate step_id')
        ruleids = [r.rule_id for r in self.rules]
        if len(ruleids) != len(set(ruleids)):
            raise ConfigurationError('rules: duplicate rule_id')
        for s in self.steps:
            if any(t not in ids for t in s.expected_next):
                raise ConfigurationError('steps.expected_next: unknown step')
        if not isinstance(self.baseline,Mapping) or len(self.baseline) > 128:
            raise ConfigurationError('baseline: explicit metric/value mapping required')
        for metric,value in self.baseline.items():
            identifier(metric,'baseline.metric',ConfigurationError)
            if not finite(value):
                raise ConfigurationError(f'baseline.{metric}: finite numeric value required')
        for rule in self.rules:
            if rule.metric not in self.baseline:
                raise ConfigurationError(f'rules.{rule.rule_id}: missing manual baseline')
            if rule.reference == 'relative' and self.baseline[rule.metric] == 0:
                raise ConfigurationError('rules.reference: relative baseline cannot be zero')
            if rule.persistence > self.max_events:
                raise ConfigurationError('rules.persistence: exceeds max_events')
            if rule.step_id is not None and rule.step_id not in ids:
                raise ConfigurationError(f'rules.{rule.rule_id}: unknown step_id')
        object.__setattr__(self,'baseline',MappingProxyType(dict(self.baseline)))
        for name in ('window_seconds','ttl_seconds'):
            positive(getattr(self,name),name)
        positive(self.max_lateness_seconds,'max_lateness_seconds',zero=True)
        if self.ttl_seconds < self.window_seconds + self.max_lateness_seconds:
            raise ConfigurationError('ttl_seconds: must cover window and permitted lateness')
        for name in ('max_events','max_trajectories','max_payload_bytes','max_evidence_refs','max_findings'):
            if type(getattr(self,name)) is not int or getattr(self,name) < 1:
                raise ConfigurationError(f'{name}: positive integer required')
        if any(r.min_samples > self.max_events for r in self.rules):
            raise ConfigurationError('rules.min_samples: exceeds max_events')

    @classmethod
    def from_dict(cls,data):
        if not isinstance(data,Mapping):
            raise ConfigurationError('config: object required')
        values = dict(data)
        for name,kind in (('steps',JourneyStep),('rules',ThresholdRule)):
            if name in values:
                if not isinstance(values[name],(list,tuple)):
                    raise ConfigurationError(f'{name}: array required')
                values[name] = tuple(strict(kind,item) for item in values[name])
        return strict(cls,values)

    def to_dict(self):
        result = {f.name:getattr(self,f.name) for f in fields(self)}
        result['baseline'] = dict(self.baseline)
        for name in ('steps','rules'):
            result[name] = [{f.name:(list(getattr(x,f.name)) if isinstance(getattr(x,f.name),tuple) else getattr(x,f.name)) for f in fields(x)} for x in getattr(self,name)]
        return result

    @property
    def configuration_hash(self):
        import hashlib, json
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()).hexdigest()

    model_validate = from_dict
    def model_dump(self, **kwargs):
        return self.to_dict()
