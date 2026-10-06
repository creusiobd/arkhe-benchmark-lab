"""Deterministic, serial observation engine. Never executes business actions."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import operator
from .config import JourneyConfig
from .contracts import TrajectoryEvent, TrajectoryAssessment, RuleFinding, aware, identifier
from .errors import EventValidationError, DuplicateEventError, ConfigurationError
from .state import BoundedTrajectoryState

OPS = {'gt': operator.gt, 'ge': operator.ge, 'lt': operator.lt, 'le': operator.le}


def aggregate(samples, metric, kind):
    values = [event.metrics[metric] for event in samples]
    if not values:
        return None
    try:
        if kind == 'latest':
            result = values[-1]
        elif kind == 'max':
            result = max(values)
        elif kind == 'min':
            result = min(values)
        elif kind == 'mean':
            result = math.fsum(value / len(values) for value in values)
        else:
            if len(samples) < 2:
                return None
            start = samples[0].event_time
            xs = [(event.event_time - start).total_seconds() for event in samples]
            mean_x = math.fsum(x / len(xs) for x in xs)
            mean_y = math.fsum(value / len(values) for value in values)
            denominator = math.fsum((x - mean_x) ** 2 for x in xs)
            if denominator <= 0:
                return None
            result = math.fsum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values)) / denominator
        return float(result) if math.isfinite(result) else None
    except (OverflowError, ValueError):
        return None


class JourneyEngine:
    def __init__(self, config, clock=None, state=None):
        self.config = JourneyConfig.from_dict(config.to_dict() if isinstance(config, JourneyConfig) else config)
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        if state is not None and state.config.to_dict() != self.config.to_dict():
            raise ConfigurationError('state: configuration mismatch')
        self.state = state or BoundedTrajectoryState(self.config, self.clock)
        self.steps = {step.step_id: step for step in self.config.steps}
        self._last_clock = None
        self._configuration_hash = self.config.configuration_hash

    def _now(self):
        now = aware(self.clock(), 'clock')
        if self._last_clock is not None and now < self._last_clock:
            raise EventValidationError('clock: moved backwards')
        self._last_clock = now
        return now

    def _key(self, tenant, trajectory):
        identifier(trajectory, 'trajectory_id')
        if tenant != self.config.tenant_id:
            raise EventValidationError('tenant_id: configuration mismatch')
        return (tenant, self.config.journey_id, self.config.version, trajectory)

    def _assessment(self, trajectory, at, status, **kwargs):
        return TrajectoryAssessment(tenant_id=self.config.tenant_id,
            journey_id=self.config.journey_id, journey_version=self.config.version,
            trajectory_id=trajectory, evaluated_at=at, status=status,
            configuration_hash=self._configuration_hash, **kwargs)

    def ingest(self, event):
        # Reconstruct even typed instances: validation and detached immutable maps.
        event = TrajectoryEvent.from_dict(event.to_dict() if isinstance(event, TrajectoryEvent) else event)
        if event.journey_id != self.config.journey_id or event.journey_version != self.config.version:
            raise EventValidationError('journey identity/version: configuration mismatch')
        key = self._key(event.tenant_id, event.trajectory_id)
        if event.step_id not in self.steps:
            raise EventValidationError('step_id: unknown configured step')
        now = self._now()
        if event.event_time > now or event.ingested_at > now:
            raise EventValidationError('event timestamps: future evidence rejected')
        encoded = json.dumps(event.to_dict(), sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()
        if len(encoded) > self.config.max_payload_bytes:
            raise EventValidationError('event: payload limit exceeded')
        digest = hashlib.sha256(encoded).hexdigest()
        state = self.state.get(key, now)
        if event.event_id in state.fingerprints:
            if state.fingerprints[event.event_id] != digest:
                raise DuplicateEventError('event_id: conflicting content')
            return state.assessments[event.event_id]
        if len(state.events) >= self.config.max_events:
            state.context_loss_reason = 'event_capacity_exceeded'
            return self._assessment(event.trajectory_id, now, 'insufficient_evidence',
                context_loss_reason=state.context_loss_reason)
        latest = max((e.event_time for e in state.events.values()), default=event.event_time)
        if (latest - event.event_time).total_seconds() > self.config.max_lateness_seconds:
            state.context_loss_reason = state.context_loss_reason or 'lateness_exceeded'
        # Arrival latency is permitted; lateness measures distance behind stream watermark.
        state.events[event.event_id] = event
        state.fingerprints[event.event_id] = digest
        result = self._evaluate(event.trajectory_id, state, max(latest, event.event_time), now)
        state.assessments[event.event_id] = result
        return result

    def check(self, tenant_id, trajectory_id, as_of=None):
        now = self._now()
        at = aware(as_of, 'as_of') if as_of is not None else now
        if at > now:
            raise EventValidationError('as_of: future evaluation rejected')
        key = self._key(tenant_id, trajectory_id)
        state = self.state.find(key, now)
        if state is None:
            reason = self.state.tombstones.get(key, 'trajectory_unknown')
            if self.state.loss_registry_overflow and reason == 'trajectory_unknown':
                reason = 'loss_registry_overflow'
            return self._assessment(trajectory_id, at, 'insufficient_evidence', context_loss_reason=reason)
        return self._evaluate(trajectory_id, state, at, at)

    def _rule_value(self, rule, samples):
        if rule.aggregation == 'latest' and samples:
            latest_values = {event.metrics[rule.metric] for event in samples if event.event_time == samples[-1].event_time}
            if len(latest_values) > 1:
                return None, None
        observed = aggregate(samples, rule.metric, rule.aggregation)
        if observed is None:
            return None, None
        baseline = self.config.baseline[rule.metric]
        try:
            compared = (observed if rule.reference == 'absolute' else
                observed - baseline if rule.reference == 'delta' else
                (observed - baseline) / abs(baseline))
            return (observed, compared) if math.isfinite(compared) else (None, None)
        except (OverflowError, ValueError):
            return None, None

    def _evaluate(self, trajectory, state, watermark, evaluated_at):
        all_events = sorted((event for event in state.events.values()
            if event.event_time <= watermark and event.ingested_at <= evaluated_at),
            key=lambda event: (event.event_time, event.event_id))
        window = [event for event in all_events if (watermark - event.event_time).total_seconds() <= self.config.window_seconds]
        findings, missing = [], []
        if (evaluated_at - watermark).total_seconds() > self.config.window_seconds:
            missing.append('telemetry_stale')
        ambiguous = any(a.event_time == b.event_time and a.step_id != b.step_id for a, b in zip(all_events, all_events[1:]))
        # All caches are evaluation-local: no data leaks across windows/as_of.
        sample_cache, value_cache, prefix_cache, evidence_cache = {}, {}, {}, {}
        def samples_for(metric, step_id=None):
            key = (metric, step_id)
            if key not in sample_cache:
                sample_cache[key] = [event for event in window if metric in event.metrics
                    and (step_id is None or event.step_id == step_id)]
            return sample_cache[key]
        def value_for(rule, samples):
            key = (rule.metric, rule.step_id, rule.aggregation, rule.reference)
            if key not in value_cache:
                value_cache[key] = self._rule_value(rule, samples)
            return value_cache[key]
        trends = {}
        for metric in self.config.baseline:
            value = aggregate(samples_for(metric), metric, 'slope')
            if value is not None:
                trends[metric] = value
        for rule in self.config.rules:
            samples = samples_for(rule.metric, rule.step_id)
            observed, compared = value_for(rule, samples)
            if len(samples) < rule.min_samples or observed is None:
                missing.append(rule.metric + ':' + rule.rule_id)
                continue
            holds = OPS[rule.operator](compared, rule.threshold)
            if holds and rule.persistence > 1:
                if len(samples) < rule.persistence:
                    holds = False
                else:
                    for index in range(len(samples) - rule.persistence, len(samples)):
                        key = (rule.metric, rule.step_id, rule.aggregation, rule.reference, index)
                        if key not in prefix_cache:
                            prefix = samples[:index + 1]
                            end = prefix[-1].event_time
                            prefix = [event for event in prefix if (end - event.event_time).total_seconds() <= self.config.window_seconds]
                            prefix_cache[key] = (len(prefix), self._rule_value(rule, prefix)[1])
                        count, value = prefix_cache[key]
                        if count < rule.min_samples or value is None or not OPS[rule.operator](value, rule.threshold):
                            holds = False
                            break
            if holds:
                key = (rule.metric, rule.step_id)
                if key not in evidence_cache:
                    evidence_cache[key] = tuple(event.event_id for event in samples[-self.config.max_evidence_refs:])
                findings.append(RuleFinding(rule_id=rule.rule_id, metric=rule.metric,
                    observed=observed, baseline=self.config.baseline[rule.metric], threshold=rule.threshold,
                    reason='threshold_exceeded', severity=rule.severity,
                    evidence_event_ids=evidence_cache[key], aggregation=rule.aggregation,
                    reference=rule.reference, comparison_value=compared, sample_count=len(samples),
                    evidence_truncated=len(samples) > self.config.max_evidence_refs,
                    elapsed_seconds=(samples[-1].event_time - samples[0].event_time).total_seconds()))
        absent = []
        if all_events:
            # Consecutive repeats represent observations of a step, not new workflow transitions.
            segments = []
            for event in all_events:
                if not segments or event.step_id != segments[-1].step_id:
                    segments.append(event)
            for index, event in enumerate(segments):
                step = self.steps[event.step_id]
                successor = segments[index + 1] if index + 1 < len(segments) else None
                if successor is not None and successor.event_time > event.event_time and successor.step_id not in step.expected_next:
                    findings.append(RuleFinding(rule_id='transition:' + step.step_id, metric='journey_transition',
                        observed=None, baseline=None, threshold=0, reason='unexpected_transition',
                        evidence_event_ids=(event.event_id, successor.event_id)[-self.config.max_evidence_refs:],
                        evidence_truncated=self.config.max_evidence_refs < 2, sample_count=2))
                if step.max_delay_seconds is None:
                    continue
                delay = ((successor.event_time - event.event_time).total_seconds() if successor is not None
                    else (watermark - event.event_time).total_seconds())
                if delay > step.max_delay_seconds + (0 if successor is not None else self.config.max_lateness_seconds):
                    if successor is None:
                        absent.extend(step.expected_next)
                    findings.append(RuleFinding(rule_id='deadline:' + step.step_id, metric='journey_delay_seconds',
                        observed=delay, baseline=None, threshold=step.max_delay_seconds, reason='step_deadline_exceeded',
                        evidence_event_ids=((event.event_id,) if successor is None else (event.event_id, successor.event_id))[-self.config.max_evidence_refs:],
                        evidence_truncated=successor is not None and self.config.max_evidence_refs < 2,
                        sample_count=1 if successor is None else 2))
        # Known deviations remain evidence even when the overall result cannot assert full coverage.
        insufficient = state.context_loss_reason or not window or missing or absent or ambiguous
        status = 'insufficient_evidence' if insufficient else 'deviation' if findings else 'normal'
        total_findings = len(findings)
        return self._assessment(trajectory, evaluated_at, status, findings=tuple(findings[-self.config.max_findings:]),
            total_findings=total_findings, findings_truncated=total_findings > self.config.max_findings, trends=trends,
            missing_expected_steps=tuple(dict.fromkeys(absent)), context_loss_reason=state.context_loss_reason or ('ambiguous_step_order' if ambiguous else None),
            missing_metrics=tuple(dict.fromkeys(missing)), window_end=watermark)


TrajectoryEngine = JourneyEngine
