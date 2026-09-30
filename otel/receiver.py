import logging
from typing import Any, Dict
from fastapi import APIRouter, Header, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse

from .adapter import OTelLyapunovAdapter
from .exporter import OTelEnrichedExporter

logger = logging.getLogger("ArkheOTelReceiver")

otel_router = APIRouter(prefix="", tags=["OpenTelemetry Protocol"])
otel_adapter = OTelLyapunovAdapter(pool_capacity=30)
otel_exporter = OTelEnrichedExporter()

# Referência injetável para a função build_telemetry_payload do app principal
_global_payload_builder = None

def set_payload_builder(builder_fn):
    global _global_payload_builder
    _global_payload_builder = builder_fn

@otel_router.post("/v1/traces")
async def receive_otlp_traces(request: Request):
    """
    Ingestor compatível com OpenTelemetry Protocol (OTLP/HTTP JSON).
    Recebe spans de traces de qualquer OTel SDK ou OTel Collector corporativo.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Payload JSON OTLP inválido")

    spans = otel_adapter.parse_otlp_json(payload)
    if not spans:
        # Se for formato simplificado/flat
        return {"status": "accepted", "spans_ingested": 0}

    observables = otel_adapter.ingest_spans(spans)
    logger.debug(f"📥 [OTel Ingestion] {len(spans)} spans processados. Rho estimado={observables['resources']['antifraud_pool_utilization_ratio']}")

    return {
        "status": "accepted",
        "spans_ingested": len(spans),
        "inferred_state": {
            "rho": observables["resources"]["antifraud_pool_utilization_ratio"],
            "wq_ws_ratio": observables["queueing"]["wq_ws_ratio"],
            "p95_ms": observables["latency_ms"]["p95"]
        }
    }

@otel_router.post("/v1/metrics")
async def receive_otlp_metrics(request: Request):
    """
    Ingestor compatível com OTLP/HTTP Metrics.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Payload JSON OTLP inválido")

    return {"status": "accepted", "metrics_ingested": len(payload.get("resourceMetrics", []))}

@otel_router.get("/metrics", response_class=PlainTextResponse)
@otel_router.get("/v1/arkhe/metrics", response_class=PlainTextResponse)
async def export_prometheus_metrics():
    """
    Exposição de métricas padrão OpenMetrics / Prometheus.
    Permite raspagem direta por Prometheus Server, Datadog Agent ou Grafana Agent.
    """
    if _global_payload_builder:
        payload = await _global_payload_builder()
    else:
        obs = otel_adapter.compute_observables()
        payload = {
            "telemetry": obs,
            "sentinel": {"score": 5.0, "level": "healthy"},
            "sre_governance": {"current_sli_availability_pct": 100.0, "error_budget_remaining_pct": 100.0, "burn_rate": 0.0},
            "mitigation": {"active": False, "fast_path_active": False},
            "projection": {"time_to_collapse_sec": 9999.0, "d_rho_dt_per_min": 0.0}
        }

    return otel_exporter.generate_prometheus_text(payload)
