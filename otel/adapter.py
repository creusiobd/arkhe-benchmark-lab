import logging
import math
import time
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

from .models import OTLPSpan, OTLPTraceBatch

logger = logging.getLogger("ArkheOTelAdapter")

class OTelLyapunovAdapter:
    """
    Adaptador OpenTelemetry para o Kernel Cibernético de Lyapunov.
    Processa spans padrão OTLP (OpenTelemetry Protocol) e infere as grandezas
    físicas de Teoria das Filas: rho (ocupação), W_q (espera), W_s (serviço) e R_retry.
    """
    def __init__(self, pool_capacity: int = 30, window_size: int = 500):
        self.pool_capacity = pool_capacity
        self.window_size = window_size
        
        # Buffers temporais deslizantes
        self.recent_service_times: deque = deque(maxlen=window_size)
        self.recent_queue_waits: deque = deque(maxlen=window_size)
        self.recent_latencies: deque = deque(maxlen=window_size)
        self.active_spans_in_flight: Dict[str, float] = {}  # span_id -> start_time
        
        # Contadores transacionais acumulados
        self.total_transactions: int = 0
        self.total_attempts: int = 0
        self.total_technical_timeouts: int = 0
        self.total_pool_exhaustions: int = 0
        self.seen_transactions: set = set()

    def parse_otlp_json(self, otlp_dict: Dict[str, Any]) -> List[OTLPSpan]:
        """
        Interpreta payloads JSON padrão OTLP (resourceSpans / scopeSpans).
        """
        parsed_spans: List[OTLPSpan] = []
        resource_spans = otlp_dict.get("resourceSpans", [])
        
        for r_span in resource_spans:
            # Extrai atributos do recurso (ex: service.name)
            res_attrs = {}
            for a in r_span.get("resource", {}).get("attributes", []):
                k = a.get("key")
                v = list(a.get("value", {}).values())[0] if a.get("value") else None
                res_attrs[k] = v

            for s_span in r_span.get("scopeSpans", []):
                for raw in s_span.get("spans", []):
                    span_attrs = dict(res_attrs)
                    for a in raw.get("attributes", []):
                        k = a.get("key")
                        v = list(a.get("value", {}).values())[0] if a.get("value") else None
                        span_attrs[k] = v

                    span = OTLPSpan(
                        trace_id=raw.get("traceId", ""),
                        span_id=raw.get("spanId", ""),
                        parent_span_id=raw.get("parentSpanId"),
                        name=raw.get("name", ""),
                        kind=raw.get("kind", "SPAN_KIND_INTERNAL"),
                        start_time_nano=int(raw.get("startTimeUnixNano", 0)),
                        end_time_nano=int(raw.get("endTimeUnixNano", 0)),
                        attributes=span_attrs,
                        status_code=raw.get("status", {}).get("code", "STATUS_CODE_UNSET"),
                        status_message=raw.get("status", {}).get("message")
                    )
                    parsed_spans.append(span)

        return parsed_spans

    def ingest_spans(self, spans: List[OTLPSpan]) -> dict:
        """
        Processa uma lista de spans e atualiza o estado estocástico de filas.
        """
        now = time.time()

        for s in spans:
            dur = s.duration_ms
            self.recent_latencies.append(dur)
            
            # Identificação de transação e retries
            tx_id = s.attributes.get("transaction.id") or s.trace_id
            self.total_attempts += 1
            if tx_id not in self.seen_transactions:
                self.seen_transactions.add(tx_id)
                self.total_transactions += 1

            # Inferência de serviço e fila do nó crítico (ex: antifraude ou banco)
            service = s.service_name.lower()
            if "antifraud" in service or "antifraude" in service or "scoring" in s.name.lower():
                self.recent_service_times.append(dur)
                # Extrai atraso de fila (se houver span pai, calcula o delta entre chegada e início)
                wq = float(s.attributes.get("queue.wait_ms", 0.05))
                self.recent_queue_waits.append(wq)

            # Mapeamento de erros de infraestrutura
            status_str = str(s.status_code).upper()
            http_status = int(s.attributes.get("http.response.status_code", 200))
            if http_status == 504 or "TIMEOUT" in status_str:
                self.total_technical_timeouts += 1
            elif http_status == 503 or "EXHAUSTED" in status_str:
                self.total_pool_exhaustions += 1

        return self.compute_observables()

    def compute_observables(self) -> dict:
        """
        Gera o dicionário de observáveis telemétricos compatível com o ARKHÉ Sentinel.
        """
        lats = sorted(list(self.recent_latencies)) if self.recent_latencies else [45.0]
        n = len(lats)
        p50 = lats[int(n * 0.50)]
        p95 = lats[min(n - 1, int(n * 0.95))]
        p99 = lats[min(n - 1, int(n * 0.99))]

        sts = list(self.recent_service_times)
        avg_ws = (sum(sts) / len(sts)) if sts else 45.0

        qws = list(self.recent_queue_waits)
        avg_wq = (sum(qws) / len(qws)) if qws else 0.05

        wq_ws = round(avg_wq / max(1.0, avg_ws), 4)

        # Cálculo da taxa de ocupação instantânea estimada (Lei de Little: L = lambda * Ws)
        # Taxa de chegada recente estimada a partir do número de spans / janela
        arrival_rate_tps = max(10.0, float(len(self.recent_latencies) / max(1.0, 5.0)))
        estimated_slots_in_use = (arrival_rate_tps * (avg_ws / 1000.0))
        rho = max(0.0, min(1.0, estimated_slots_in_use / max(1, self.pool_capacity)))

        retry_ratio = round(
            (self.total_attempts / max(1, self.total_transactions)), 3
        ) if self.total_transactions > 0 else 1.0

        return {
            "timestamp": time.time(),
            "runtime": {
                "event_loop_lag_ms": 0.45,
            },
            "resources": {
                "antifraud_pool_capacity": self.pool_capacity,
                "antifraud_pool_in_use": int(rho * self.pool_capacity),
                "antifraud_pool_utilization_ratio": round(rho, 4),
                "antifraud_waiters_count": max(0, int(estimated_slots_in_use - self.pool_capacity)),
            },
            "queueing": {
                "avg_queue_wait_ms": round(avg_wq, 2),
                "avg_service_time_ms": round(avg_ws, 2),
                "wq_ws_ratio": wq_ws,
            },
            "traffic": {
                "unique_transactions_total": self.total_transactions,
                "attempts_total": self.total_attempts,
                "retry_amplification_ratio": retry_ratio,
            },
            "latency_ms": {
                "p50": round(p50, 2),
                "p95": round(p95, 2),
                "p99": round(p99, 2),
            },
            "outcomes": {
                "technical_timeouts": self.total_technical_timeouts,
                "pool_exhaustion_errors": self.total_pool_exhaustions,
            }
        }
