"""Local configurable dictionary mapping; does not connect to any infrastructure."""
from .contracts import TrajectoryEvent
from .errors import EventValidationError


def _read(payload, path):
    current = payload
    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            raise EventValidationError(f"mapped field absent: {path}")
        current = current[key]
    return current


class MappingAdapter:
    def __init__(self, mapping=None, metric_mapping=None, dimension_mapping=None):
        self.mapping = dict(mapping or {})
        self.metric_mapping = dict(metric_mapping or {})
        self.dimension_mapping = dict(dimension_mapping or {})

    def adapt(self, payload):
        fields = {}
        for field in ("tenant_id", "journey_id", "journey_version", "trajectory_id", "event_id",
                      "step_id", "event_time", "ingested_at"):
            fields[field] = _read(payload, self.mapping.get(field, field))
        fields["metrics"] = ({name: _read(payload, path) for name, path in self.metric_mapping.items()}
                             if self.metric_mapping else payload.get("metrics", {}))
        fields["dimensions"] = ({name: _read(payload, path) for name, path in self.dimension_mapping.items()}
                                if self.dimension_mapping else payload.get("dimensions", {}))
        fields["outcome"] = _read(payload, self.mapping["outcome"]) if "outcome" in self.mapping else payload.get("outcome")
        return TrajectoryEvent.from_dict(fields)
