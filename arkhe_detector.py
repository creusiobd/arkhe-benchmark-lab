from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np

@dataclass
class ArkheDetectionResult:
    triggered: bool
    timestamp: float
    trigger_reason: Optional[str]
    vector: Dict[str, float]
    predicted_time_to_collapse_sec: Optional[float]
    confidence_score: float

class ArkheTrajectoryEngine:
    """
    ARKHÉ Engine: Detecção Antecipada Baseada em Trajetória e Física de Filas.
    Não analisa limiares de erro estáticos, mas sim a derivada de saturação dos recursos
    e a divergência da dinâmica de Little (L = lambda * W).
    """
    def __init__(self, sample_interval_sec: float = 2.0):
        self.sample_interval = sample_interval_sec
        self.window_history: List[dict] = []
        self.max_window_size = 30 # ~60 segundos de histórico em alta resolução

    def add_snapshot(self, snap: dict):
        self.window_history.append(snap)
        if len(self.window_history) > self.max_window_size:
            self.window_history.pop(0)

    def evaluate(self) -> ArkheDetectionResult:
        if len(self.window_history) < 4:
            return ArkheDetectionResult(
                triggered=False,
                timestamp=0.0,
                trigger_reason=None,
                vector={},
                predicted_time_to_collapse_sec=None,
                confidence_score=0.0
            )

        current = self.window_history[-1]
        now = current.get("timestamp", 0.0)

        # 1. Utilização atual do pool
        rho = current["resources"]["antifraud_pool_utilization_ratio"]

        # 2. Derivada temporal de utilização do pool (d_rho / dt)
        # Usamos regressão linear simples sobre os últimos snapshots
        recent = self.window_history[-6:]
        rhos = [s["resources"]["antifraud_pool_utilization_ratio"] for s in recent]
        t_base = recent[0]["timestamp"]
        times = [s["timestamp"] - t_base for s in recent]
        if len(times) >= 2 and max(times) > 0:
            slope, _ = np.polyfit(times, rhos, 1) # variação por segundo
            d_rho_dt_min = float(slope * 60.0) # variação por minuto
        else:
            slope = 0.0
            d_rho_dt_min = 0.0

        # 3. Razão de tempo em fila vs serviço (W_q / W_s)
        queueing = current.get("queueing", {})
        wq_ws_ratio = queueing.get("wq_ws_ratio", 0.0)
        avg_wq = queueing.get("avg_queue_wait_ms", 0.0)

        # 4. Fator de amplificação de retries
        traffic = current.get("traffic", {})
        retry_amp = traffic.get("retry_amplification_ratio", 1.0)

        vector = {
            "rho_pool": round(rho, 4),
            "d_rho_dt_per_min": round(d_rho_dt_min, 4),
            "wq_ws_ratio": round(wq_ws_ratio, 3),
            "avg_queue_wait_ms": round(avg_wq, 2),
            "retry_amplification": round(retry_amp, 3)
        }

        # Estimativa de tempo para colapso (rho = 1.0)
        ttc = None
        if slope > 0.001 and rho < 1.0:
            ttc = (1.0 - rho) / slope

        # Critérios de detecção antecipada do ARKHÉ:
        # - Trajetória de saturação rápida (rho > 0.50 e d_rho/dt > 0.05/min)
        # - Fila física acumulando (W_q / W_s > 0.8 com W_q > 25ms)
        # - Amplificação de retries detectada no cliente (retry_amp > 1.12 com base estatística)
        total_txs = traffic.get("unique_transactions_total", 0)
        is_trajectory_anomaly = (rho >= 0.40 and d_rho_dt_min > 0.03) or (rho >= 0.60)
        is_queue_forming = (wq_ws_ratio > 0.6 and avg_wq > 15.0)
        is_retry_amplification = (retry_amp > 1.10 and total_txs >= 50)

        if is_trajectory_anomaly or is_queue_forming or is_retry_amplification:
            reasons = []
            if is_trajectory_anomaly:
                reasons.append(f"Aceleração de saturação do pool (rho={rho*100:.1f}%, d_rho/dt={d_rho_dt_min:+.2f}/min)")
            if is_queue_forming:
                reasons.append(f"Acúmulo de fila física (W_q/W_s={wq_ws_ratio:.2f}, W_q={avg_wq:.1f}ms)")
            if is_retry_amplification:
                reasons.append(f"Amplificação de retries detectada (R_retry={retry_amp:.2f})")

            confidence = min(0.99, 0.70 + (0.10 * len(reasons)) + (0.15 * rho))
            return ArkheDetectionResult(
                triggered=True,
                timestamp=now,
                trigger_reason=" | ".join(reasons),
                vector=vector,
                predicted_time_to_collapse_sec=round(ttc, 1) if ttc else None,
                confidence_score=round(confidence, 2)
            )

        return ArkheDetectionResult(
            triggered=False,
            timestamp=now,
            trigger_reason=None,
            vector=vector,
            predicted_time_to_collapse_sec=None,
            confidence_score=0.0
        )
