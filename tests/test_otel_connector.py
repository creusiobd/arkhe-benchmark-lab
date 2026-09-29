import unittest
from fastapi.testclient import TestClient

from app import app
from otel.models import OTLPSpan
from otel.adapter import OTelLyapunovAdapter
from otel.exporter import OTelEnrichedExporter

class TestOpenTelemetryConnector(unittest.TestCase):
    def setUp(self):
        self.adapter = OTelLyapunovAdapter(pool_capacity=30)
        self.exporter = OTelEnrichedExporter()
        self.client = TestClient(app)

    def _generate_mock_otlp_payload(self, service_name: str, duration_ms: float, count: int = 10, error: bool = False):
        spans = []
        base_time_nano = 1727480000000000000
        for i in range(count):
            start = base_time_nano + (i * 50_000_000)
            end = start + int(duration_ms * 1_000_000)
            spans.append({
                "traceId": f"4bf92f3577b34da6a3ce929d0e0e473{i:02d}",
                "spanId": f"00f067aa0ba902b{i:02d}",
                "name": f"HTTP POST /v1/{service_name}",
                "kind": "SPAN_KIND_SERVER",
                "startTimeUnixNano": str(start),
                "endTimeUnixNano": str(end),
                "attributes": [
                  {"key": "service.name", "value": {"stringValue": service_name}},
                  {"key": "http.response.status_code", "value": {"intValue": 504 if error else 200}},
                  {"key": "queue.wait_ms", "value": {"doubleValue": 12.5 if error else 0.2}}
                ],
                "status": {"code": "STATUS_CODE_ERROR" if error else "STATUS_CODE_OK"}
            })

        return {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": service_name}}
                        ]
                    },
                    "scopeSpans": [{"spans": spans}]
                }
            ]
        }

    def test_otlp_json_parsing(self):
        """Valida que o parser OTLP extrai corretamente spans aninhados padrão OTel."""
        payload = self._generate_mock_otlp_payload("antifraud-scoring", 45.0, count=5)
        parsed = self.adapter.parse_otlp_json(payload)
        
        self.assertEqual(len(parsed), 5)
        self.assertEqual(parsed[0].service_name, "antifraud-scoring")
        self.assertAlmostEqual(parsed[0].duration_ms, 45.0, places=1)
        self.assertEqual(parsed[0].attributes.get("http.response.status_code"), 200)

    def test_lyapunov_observables_inference(self):
        """Valida que a ingestão de spans OTLP infere rho, Ws e Wq/Ws para a Bacia de Estabilidade."""
        # 1. Ingestão de regime nominal (45ms)
        nominal_payload = self._generate_mock_otlp_payload("antifraud", 45.0, count=20)
        spans_nominal = self.adapter.parse_otlp_json(nominal_payload)
        obs_nominal = self.adapter.ingest_spans(spans_nominal)

        self.assertLess(obs_nominal["resources"]["antifraud_pool_utilization_ratio"], 0.40)
        self.assertLess(obs_nominal["queueing"]["wq_ws_ratio"], 0.10)
        self.assertAlmostEqual(obs_nominal["queueing"]["avg_service_time_ms"], 45.0, places=1)

        # 2. Ingestão de regime com drift severo (255ms)
        drift_payload = self._generate_mock_otlp_payload("antifraud", 255.0, count=30)
        spans_drift = self.adapter.parse_otlp_json(drift_payload)
        obs_drift = self.adapter.ingest_spans(spans_drift)

        # Ws e Rho devem aumentar significativamente refletindo a degradação
        self.assertGreater(obs_drift["queueing"]["avg_service_time_ms"], 100.0)
        self.assertGreater(obs_drift["resources"]["antifraud_pool_utilization_ratio"], obs_nominal["resources"]["antifraud_pool_utilization_ratio"])

    def test_prometheus_exposition_format(self):
        """Valida a geração de métricas enriquecidas no padrão Prometheus/OpenMetrics."""
        sample_payload = {
            "telemetry": {
                "resources": {"antifraud_pool_utilization_ratio": 0.533},
                "queueing": {"wq_ws_ratio": 0.025}
            },
            "sentinel": {"score": 88.0, "level": "critical"},
            "sre_governance": {
                "current_sli_availability_pct": 100.0,
                "error_budget_remaining_pct": 100.0,
                "burn_rate": 0.0
            },
            "mitigation": {"active": True, "fast_path_active": True},
            "projection": {"time_to_collapse_sec": 2.0, "d_rho_dt_per_min": 14.91}
        }

        prom_text = self.exporter.generate_prometheus_text(sample_payload)

        self.assertIn("arkhe_sentinel_risk_score", prom_text)
        self.assertIn("88.0", prom_text)
        self.assertIn("arkhe_lyapunov_pool_utilization_rho 0.533", prom_text)
        self.assertIn("arkhe_predicted_time_to_collapse_seconds 2.0", prom_text)
        self.assertIn("arkhe_closed_loop_mitigation_active 1", prom_text)
        self.assertIn("arkhe_closed_loop_fast_path_active 1", prom_text)

    def test_http_endpoint_metrics(self):
        """Valida o endpoint GET /metrics respondendo com status 200 e texto Prometheus."""
        res = self.client.get("/metrics")
        self.assertEqual(res.status_code, 200)
        self.assertIn("arkhe_sentinel_risk_score", res.text)
        self.assertIn("arkhe_lyapunov_pool_utilization_rho", res.text)

    def test_http_endpoint_v1_traces_ingestion(self):
        """Valida o endpoint POST /v1/traces recebendo payload padrão OTLP HTTP JSON."""
        payload = self._generate_mock_otlp_payload("antifraud-worker", 50.0, count=5)
        res = self.client.post("/v1/traces", json=payload)
        
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "accepted")
        self.assertEqual(data["spans_ingested"], 5)
        self.assertIn("inferred_state", data)

if __name__ == "__main__":
    unittest.main()
