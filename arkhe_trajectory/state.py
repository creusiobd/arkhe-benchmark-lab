"""Bounded process-local observation history. Serial use, no durable replay guarantee."""
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ObservationState:
    touched_at: datetime
    events: dict = field(default_factory=dict)
    fingerprints: dict = field(default_factory=dict)
    assessments: dict = field(default_factory=dict)
    usable_ids: list = field(default_factory=list)
    persistence: dict = field(default_factory=dict)
    last_event_id: str | None = None
    context_loss_reason: str | None = None


class BoundedTrajectoryState:
    def __init__(self, config, clock=None):
        self.config = config
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.trajectories = OrderedDict()
        self.tombstones = OrderedDict()
        self.loss_registry_overflow = False

    def _lost(self, key, reason):
        self.tombstones[key] = reason
        self.tombstones.move_to_end(key)
        if len(self.tombstones) > self.config.max_trajectories:
            self.tombstones.popitem(last=False)
            self.loss_registry_overflow = True

    def expire(self, now):
        for key, state in list(self.trajectories.items()):
            if (now - state.touched_at).total_seconds() >= self.config.ttl_seconds:
                self.trajectories.pop(key)
                self._lost(key, "ttl_expired")

    def get(self, key, now):
        self.expire(now)
        if key not in self.trajectories:
            if len(self.trajectories) >= self.config.max_trajectories:
                evicted, _ = self.trajectories.popitem(last=False)
                self._lost(evicted, "trajectory_capacity_evicted")
            reason = self.tombstones.get(key)
            if reason is None and self.loss_registry_overflow:
                reason = "loss_registry_overflow"
            self.trajectories[key] = ObservationState(now, context_loss_reason=reason)
        state = self.trajectories[key]
        state.touched_at = now
        self.trajectories.move_to_end(key)
        return state

    def find(self, key, now):
        self.expire(now)
        return self.trajectories.get(key)

    def stats(self):
        return {"trajectory_count": len(self.trajectories),
                "events_count": sum(len(s.events) for s in self.trajectories.values()),
                "tombstones": len(self.tombstones), "loss_registry_overflow": self.loss_registry_overflow}


BoundedStateStore = BoundedTrajectoryState
