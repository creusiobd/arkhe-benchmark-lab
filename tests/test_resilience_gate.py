import unittest
from ci.resilience_gate import ResilienceGateEvaluator

class TestResilienceGate(unittest.TestCase):
    def setUp(self):
        self.evaluator = ResilienceGateEvaluator(
            max_rho=0.50,
            max_wq_ws=0.25,
            max_p95_ms=1500.0
        )

    def test_markdown_report_passed(self):
        """Valida a geração do relatório Markdown para build aprovado."""
        mock_result = {
            "passed": True,
            "metrics": {
                "total_frames": 100,
                "final_rho": 0.083,
                "max_rho_observed": 0.12,
                "avg_wq_ws_ratio": 0.005,
                "final_p95_ms": 380.0,
                "max_p95_ms": 410.0,
                "technical_errors": 0,
                "sli_availability_pct": 100.0,
                "error_budget_remaining_pct": 100.0,
                "mitigation_active": False
            },
            "checks": {
                "zero_technical_errors": True,
                "latency_p95_sla_compliant": True,
                "sli_availability_above_threshold": True,
                "error_budget_preserved": True,
                "queue_wait_ratio_acceptable": True,
                "lyapunov_basin_preserved_or_mitigated": True
            }
        }

        md = self.evaluator.generate_markdown_report(mock_result)
        self.assertIn("GATE PASSED: DEPLOY AUTHORIZED", md)
        self.assertIn("Nenhuma regressão de resiliência detectada", md)
        self.assertIn("✅ PASS", md)

    def test_markdown_report_failed(self):
        """Valida a geração do relatório Markdown para build reprovado com regressão de fila."""
        mock_result = {
            "passed": False,
            "metrics": {
                "total_frames": 100,
                "final_rho": 0.75,
                "max_rho_observed": 0.95,
                "avg_wq_ws_ratio": 0.65,
                "final_p95_ms": 1650.0,
                "max_p95_ms": 1900.0,
                "technical_errors": 14,
                "sli_availability_pct": 98.2,
                "error_budget_remaining_pct": 0.0,
                "mitigation_active": False
            },
            "checks": {
                "zero_technical_errors": False,
                "latency_p95_sla_compliant": False,
                "sli_availability_above_threshold": False,
                "error_budget_preserved": False,
                "queue_wait_ratio_acceptable": False,
                "lyapunov_basin_preserved_or_mitigated": False
            }
        }

        md = self.evaluator.generate_markdown_report(mock_result)
        self.assertIn("GATE FAILED: DEPLOY BLOCKED", md)
        self.assertIn("Regressão de resiliência detectada", md)
        self.assertIn("❌ FAIL", md)

if __name__ == "__main__":
    unittest.main()
