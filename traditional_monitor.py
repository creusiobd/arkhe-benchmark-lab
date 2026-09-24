from dataclasses import dataclass
from typing import List, Optional

@dataclass
class TraditionalAlertResult:
    triggered: bool
    timestamp: float
    trigger_rule: Optional[str]
    p95_ms: float
    error_rate: float

class TraditionalSREMonitor:
    """
    Baseline Tradicional de Mercado (Google SRE Book / Prometheus / Datadog).
    Monitores clássicos baseados em thresholds estáticos pós-impacto:
    - Monitor A: Taxa de erros técnicos (Timeouts + 503) > 5.0%
    - Monitor B: Latência P95 > 1500 ms (estouro do SLA contratual)
    """
    def __init__(self, sustained_checks_required: int = 3):
        self.sustained_checks_required = sustained_checks_required
        self.consecutive_error_violations = 0
        self.consecutive_latency_violations = 0
        self.history: List[dict] = []

    def evaluate(self, snap: dict) -> TraditionalAlertResult:
        now = snap.get("timestamp", 0.0)
        p95 = snap["latency_ms"]["p95"]

        attempts = snap["traffic"]["attempts_total"]
        timeouts = snap["outcomes"]["technical_timeouts"]
        exhaustions = snap["outcomes"]["pool_exhaustion_errors"]
        total_errors = timeouts + exhaustions

        # Se houver histórico, calcula a taxa delta entre o snapshot atual e o anterior
        if len(self.history) > 0:
            prev = self.history[-1]
            delta_attempts = attempts - prev["traffic"]["attempts_total"]
            delta_errors = total_errors - (prev["outcomes"]["technical_timeouts"] + prev["outcomes"]["pool_exhaustion_errors"])
            error_rate = (delta_errors / max(1, delta_attempts)) if delta_attempts > 0 else 0.0
        else:
            error_rate = (total_errors / max(1, attempts)) if attempts > 0 else 0.0

        self.history.append(snap)
        if len(self.history) > 30:
            self.history.pop(0)

        # Regra 1: Erros técnicos > 5%
        if error_rate >= 0.05 and attempts > 50:
            self.consecutive_error_violations += 1
        else:
            self.consecutive_error_violations = max(0, self.consecutive_error_violations - 1)

        # Regra 2: Latência P95 > 1500ms
        if p95 >= 1490.0:
            self.consecutive_latency_violations += 1
        else:
            self.consecutive_latency_violations = max(0, self.consecutive_latency_violations - 1)

        if self.consecutive_error_violations >= self.sustained_checks_required:
            return TraditionalAlertResult(
                triggered=True,
                timestamp=now,
                trigger_rule=f"Monitor A: Erros Técnicos > 5% sustentados ({error_rate*100:.1f}%)",
                p95_ms=p95,
                error_rate=error_rate
            )

        if self.consecutive_latency_violations >= self.sustained_checks_required:
            return TraditionalAlertResult(
                triggered=True,
                timestamp=now,
                trigger_rule=f"Monitor B: Latência P95 > 1500ms sustentada ({p95:.1f}ms)",
                p95_ms=p95,
                error_rate=error_rate
            )

        return TraditionalAlertResult(
            triggered=False,
            timestamp=now,
            trigger_rule=None,
            p95_ms=p95,
            error_rate=error_rate
        )
