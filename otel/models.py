from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import time

class OTelSpanKind(str, Enum):
    INTERNAL = "SPAN_KIND_INTERNAL"
    SERVER = "SPAN_KIND_SERVER"
    CLIENT = "SPAN_KIND_CLIENT"
    PRODUCER = "SPAN_KIND_PRODUCER"
    CONSUMER = "SPAN_KIND_CONSUMER"

@dataclass
class OTLPSpan:
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    name: str
    kind: str
    start_time_nano: int
    end_time_nano: int
    attributes: Dict[str, Any] = field(default_factory=dict)
    status_code: str = "STATUS_CODE_UNSET"
    status_message: Optional[str] = None

    @property
    def duration_ms(self) -> float:
        return max(0.0, (self.end_time_nano - self.start_time_nano) / 1_000_000.0)

    @property
    def service_name(self) -> str:
        return str(self.attributes.get("service.name", "unknown-service"))

@dataclass
class OTLPTraceBatch:
    spans: List[OTLPSpan] = field(default_factory=list)
    resource_attributes: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ArkheEnrichedMetric:
    name: str
    value: float
    metric_type: str  # gauge, counter, histogram
    help_text: str
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
