import time
from typing import Dict, List, Optional
import httpx

from .models import ArkheEnrichedMetric

class OTelEnrichedExporter:
    """
    Exportador de métricas cibernéticas enriquecidas do ARKHÉ.
    Converte as grandezas de Lyapunov e predições do Sentinel em métricas
    Prometheus / OpenMetrics e OTLP Metrics padrão de mercado.
    """
    def __init__(self, upstream_otlp_endpoint: Optional[str] = None):
        self.upstream_otlp_endpoint = upstream_otlp_endpoint

    def generate_prometheus_text(self, telemetry_payload: dict) -> str:
        """
        Formata o estado do ARKHÉ no padrão OpenMetrics / Prometheus.
        """
        sentinel = telemetry_payload.get("sentinel", {})
        obs = telemetry_payload.get("telemetry", {})
        res = obs.get("resources", {})
        queue = obs.get("queueing", {})
        sre = telemetry_payload.get("sre_governance", {})
        mit = telemetry_payload.get("mitigation", {})
        proj = telemetry_payload.get("projection", {})

        score = sentinel.get("score", 0.0)
        rho = res.get("antifraud_pool_utilization_ratio", 0.0)
        wq_ws = queue.get("wq_ws_ratio", 0.0)
        ttc = proj.get("time_to_collapse_sec") or 9999.0
        d_rho_dt = proj.get("d_rho_dt_per_min", 0.0)
        mit_active = 1 if mit.get("active") else 0
        fp_active = 1 if mit.get("fast_path_active") else 0
        sli = sre.get("current_sli_availability_pct", 100.0)
        budget = sre.get("error_budget_remaining_pct", 100.0)
        burn = sre.get("burn_rate", 0.0)

        lines = [
            "# HELP arkhe_sentinel_risk_score Score de risco estocástico da IA ARKHÉ Sentinel (0 a 100)",
            "# TYPE arkhe_sentinel_risk_score gauge",
            f'arkhe_sentinel_risk_score{{level="{sentinel.get("level", "healthy")}"}} {score}',
            "",
            "# HELP arkhe_lyapunov_pool_utilization_rho Taxa de ocupação de recursos críticos (rho)",
            "# TYPE arkhe_lyapunov_pool_utilization_rho gauge",
            f"arkhe_lyapunov_pool_utilization_rho {rho}",
            "",
            "# HELP arkhe_lyapunov_queue_wait_service_ratio Razão entre tempo de fila e serviço (Wq / Ws)",
            "# TYPE arkhe_lyapunov_queue_wait_service_ratio gauge",
            f"arkhe_lyapunov_queue_wait_service_ratio {wq_ws}",
            "",
            "# HELP arkhe_lyapunov_d_rho_dt_per_min Velocidade de saturação de fase (derivada temporal d_rho/dt)",
            "# TYPE arkhe_lyapunov_d_rho_dt_per_min gauge",
            f"arkhe_lyapunov_d_rho_dt_per_min {d_rho_dt}",
            "",
            "# HELP arkhe_predicted_time_to_collapse_seconds Estimativa preditiva de tempo até o colapso (TTC)",
            "# TYPE arkhe_predicted_time_to_collapse_seconds gauge",
            f"arkhe_predicted_time_to_collapse_seconds {ttc}",
            "",
            "# HELP arkhe_closed_loop_mitigation_active Flag indicando se a mitigação autônoma está ativa",
            "# TYPE arkhe_closed_loop_mitigation_active gauge",
            f"arkhe_closed_loop_mitigation_active {mit_active}",
            "",
            "# HELP arkhe_closed_loop_fast_path_active Flag indicando se o Fast-Path bypass estocástico está ativo",
            "# TYPE arkhe_closed_loop_fast_path_active gauge",
            f"arkhe_closed_loop_fast_path_active {fp_active}",
            "",
            "# HELP arkhe_sre_sli_availability_percent SLI de disponibilidade real calculada segundo Google SRE",
            "# TYPE arkhe_sre_sli_availability_percent gauge",
            f"arkhe_sre_sli_availability_percent {sli}",
            "",
            "# HELP arkhe_sre_error_budget_remaining_percent Percentual de Error Budget restante",
            "# TYPE arkhe_sre_error_budget_remaining_percent gauge",
            f"arkhe_sre_error_budget_remaining_percent {budget}",
            "",
            "# HELP arkhe_sre_burn_rate Taxa de queima do Error Budget relativo à meta contratual",
            "# TYPE arkhe_sre_burn_rate gauge",
            f"arkhe_sre_burn_rate {burn}",
            ""
        ]

        return "\n".join(lines)

    async def export_to_upstream_otlp(self, telemetry_payload: dict) -> bool:
        """
        Envia métricas para um OTel Collector upstream via OTLP HTTP se configurado.
        """
        if not self.upstream_otlp_endpoint:
            return False

        # Payload padrão OTLP Metrics JSON
        sentinel = telemetry_payload.get("sentinel", {})
        score = sentinel.get("score", 0.0)
        
        otlp_metrics_payload = {
            "resourceMetrics": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": "arkhe-cybernetic-platform"}}
                        ]
                    },
                    "scopeMetrics": [
                        {
                            "scope": {"name": "arkhe.resilience.metrics", "version": "1.0.0"},
                            "metrics": [
                                {
                                    "name": "arkhe.sentinel.score",
                                    "description": "ARKHÉ Sentinel Risk Score",
                                    "gauge": {
                                        "dataPoints": [
                                            {
                                                "timeUnixNano": str(int(time.time() * 1_000_000_000)),
                                                "asDouble": score
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.post(
                    f"{self.upstream_otlp_endpoint}/v1/metrics",
                    json=otlp_metrics_payload
                )
                return res.status_code in (200, 202)
        except Exception:
            return False
