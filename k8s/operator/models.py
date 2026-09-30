from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import time

class BasinPhase(str, Enum):
    LAMINAR_HEALTHY = "LaminarHealthy"
    DRIFT_WARNING = "DriftWarning"
    CRITICAL_BREACH = "CriticalBreach"
    MITIGATED = "Mitigated"
    RECOVERING = "Recovering"

class RuleState(str, Enum):
    ARMED = "Armed"
    TRIGGERED = "Triggered"
    IN_COOLDOWN = "InCooldown"
    DISABLED = "Disabled"

@dataclass
class WorkloadRef:
    kind: str = "Deployment"
    name: str = "payment-authorization-service"
    api_version: str = "apps/v1"

@dataclass
class StabilityConstraints:
    target_throughput_tps: float = 120.0
    max_rho_basin: float = 0.50
    max_queue_wait_ratio: float = 0.25
    critical_time_to_collapse_seconds: int = 30
    sampling_frequency_hz: int = 20

@dataclass
class PredictiveHpaConfig:
    enabled: bool = True
    min_replicas: int = 2
    max_replicas: int = 60
    scale_multiplier: float = 2.0
    cooldown_seconds: int = 120

@dataclass
class FastPathBypassConfig:
    enabled: bool = True
    traffic_bypass_ratio: float = 0.70
    target_cache_service: str = "redis-l2-cache"

@dataclass
class MitigationConfig:
    predictive_hpa: PredictiveHpaConfig = field(default_factory=PredictiveHpaConfig)
    fast_path_bypass: FastPathBypassConfig = field(default_factory=FastPathBypassConfig)

@dataclass
class TelemetrySourceConfig:
    endpoint_uri: str = "ws://127.0.0.1:8080/ws/telemetry"
    protocol: str = "websocket"

@dataclass
class ArkheStabilityBasinSpec:
    workload_ref: WorkloadRef = field(default_factory=WorkloadRef)
    stability_constraints: StabilityConstraints = field(default_factory=StabilityConstraints)
    mitigation: MitigationConfig = field(default_factory=MitigationConfig)
    telemetry_source: TelemetrySourceConfig = field(default_factory=TelemetrySourceConfig)

@dataclass
class ArkheStabilityBasinStatus:
    phase: BasinPhase = BasinPhase.LAMINAR_HEALTHY
    current_rho: float = 0.0
    current_wq_ws_ratio: float = 0.0
    d_rho_dt_per_min: float = 0.0
    time_to_collapse: str = "ESTÁVEL (∞)"
    current_replicas: int = 3
    active_mitigations: List[str] = field(default_factory=list)
    last_actuation_timestamp: Optional[str] = None
    observed_generation: int = 1

@dataclass
class ArkheStabilityBasinCR:
    name: str
    namespace: str
    spec: ArkheStabilityBasinSpec
    status: ArkheStabilityBasinStatus = field(default_factory=ArkheStabilityBasinStatus)

@dataclass
class MitigationTrigger:
    metric: str
    operator: str  # Gt, Gte, Lt, Lte, Eq
    threshold: float
    evaluation_window_seconds: int = 1

@dataclass
class MitigationAction:
    type: str  # PredictiveScaleOut, FastPathBypass, Shedding
    parameters: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ArkheMitigationRuleCR:
    name: str
    namespace: str
    target_basin_name: str
    trigger: MitigationTrigger
    action: MitigationAction
    state: RuleState = RuleState.ARMED
    trigger_count: int = 0
    last_triggered_at: Optional[str] = None
