"""Bounded in-process state. Serial use only; no durable exactly-once guarantee."""
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class TrajectoryState:
    touched_at: datetime
    events: dict = field(default_factory=dict)
    fingerprints: dict = field(default_factory=dict)
    decisions: dict = field(default_factory=dict)
    received_at: dict = field(default_factory=dict)
    principals: dict = field(default_factory=dict)
    depths: dict = field(default_factory=dict)
    observed_violation: bool = False
    first_alert_event_id: str | None = None
    context_loss_reason: str | None = None


class BoundedStateStore:
    def __init__(self, limits, clock=None):
        self.limits = limits
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.trajectories = OrderedDict()
        self.tombstones = OrderedDict()
        self.loss_registry_overflow = False

    def _lost(self, key, reason):
        self.tombstones[key] = reason
        self.tombstones.move_to_end(key)
        if len(self.tombstones) > self.limits.max_active_trajectories:
            self.tombstones.popitem(last=False)
            # Never represent an unremembered eviction as a clean new trajectory.
            self.loss_registry_overflow = True

    def get(self, key, now=None):
        now = now or self.clock()
        for stored_key, state in list(self.trajectories.items()):
            if (now - state.touched_at).total_seconds() >= self.limits.ttl_seconds:
                self.trajectories.pop(stored_key)
                self._lost(stored_key, "ttl_expired")
        if key not in self.trajectories:
            if len(self.trajectories) >= self.limits.max_active_trajectories:
                evicted, _ = self.trajectories.popitem(last=False)
                self._lost(evicted, "trajectory_capacity_evicted")
            reason = self.tombstones.get(key)
            if reason is None and self.loss_registry_overflow:
                reason = "loss_registry_overflow"
            self.trajectories[key] = TrajectoryState(now, context_loss_reason=reason)
        state = self.trajectories[key]
        state.touched_at = now
        self.trajectories.move_to_end(key)
        return state

    def mark_event_capacity(self, state):
        state.context_loss_reason = "event_capacity_exceeded"

    def stats(self):
        return {"active_trajectories": len(self.trajectories), "tombstones": len(self.tombstones),
                "events": sum(len(s.events) for s in self.trajectories.values()),
                "loss_registry_overflow": self.loss_registry_overflow}
