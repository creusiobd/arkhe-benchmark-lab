import unittest
import numpy as np
from arkhe_detector import ArkheTrajectoryEngine, ArkheDetectionResult

class TestArkheTrajectoryEngine(unittest.TestCase):
    def setUp(self):
        self.engine = ArkheTrajectoryEngine()

    def _create_snapshot(self, t: float, rho: float, wq: float = 0.05, ws: float = 45.0, retries: float = 1.0, txs: int = 100):
        return {
            "timestamp": t,
            "resources": {
                "antifraud_pool_utilization_ratio": rho,
                "antifraud_pool_capacity": 30,
                "antifraud_pool_in_use": int(rho * 30),
            },
            "queueing": {
                "avg_queue_wait_ms": wq,
                "avg_service_time_ms": ws,
                "wq_ws_ratio": wq / ws if ws > 0 else 0.0,
            },
            "traffic": {
                "unique_transactions_total": txs,
                "attempts_total": int(txs * retries),
                "retry_amplification_ratio": retries,
            },
            "latency_ms": {"p50": ws, "p95": ws * 1.2, "p99": ws * 1.5},
            "outcomes": {"technical_timeouts": 0, "pool_exhaustion_errors": 0}
        }

    def test_insufficient_history(self):
        # Menos de 4 snapshots não deve disparar falso positivo
        for i in range(3):
            self.engine.add_snapshot(self._create_snapshot(float(i), 0.12))
        res = self.engine.evaluate()
        self.assertFalse(res.triggered)
        self.assertEqual(res.confidence_score, 0.0)

    def test_nominal_state_no_trigger(self):
        # Estado nominal estável (12% de uso)
        for i in range(10):
            self.engine.add_snapshot(self._create_snapshot(float(i), 0.12, wq=0.04, ws=45.0, retries=1.0))
        res = self.engine.evaluate()
        self.assertFalse(res.triggered)
        self.assertIn("rho_pool", res.vector)
        self.assertAlmostEqual(res.vector["rho_pool"], 0.12, places=2)

    def test_drift_state_triggers_early(self):
        # Aceleração da saturação do pool (de 20% para 65% em 5 segundos)
        rhos = [0.20, 0.30, 0.42, 0.52, 0.65]
        for i, rho in enumerate(rhos):
            self.engine.add_snapshot(self._create_snapshot(float(i), rho, wq=5.0, ws=120.0, retries=1.0))
        res = self.engine.evaluate()
        self.assertTrue(res.triggered)
        self.assertGreater(res.confidence_score, 0.70)
        self.assertIn("Aceleração de saturação", res.trigger_reason)

    def test_queue_forming_triggers(self):
        # Fila física acumulando (W_q > 15ms e W_q / W_s > 0.6)
        for i in range(6):
            self.engine.add_snapshot(self._create_snapshot(float(i), 0.30, wq=35.0, ws=45.0, retries=1.0))
        res = self.engine.evaluate()
        self.assertTrue(res.triggered)
        self.assertIn("Acúmulo de fila física", res.trigger_reason)

    def test_retry_amplification_triggers(self):
        # Tempestade de retries na borda (1.25x)
        for i in range(6):
            self.engine.add_snapshot(self._create_snapshot(float(i), 0.30, wq=2.0, ws=45.0, retries=1.25, txs=200))
        res = self.engine.evaluate()
        self.assertTrue(res.triggered)
        self.assertIn("Amplificação de retries", res.trigger_reason)

if __name__ == "__main__":
    unittest.main()
