import unittest
from traditional_monitor import TraditionalSREMonitor

class TestTraditionalSREMonitor(unittest.TestCase):
    def setUp(self):
        self.monitor = TraditionalSREMonitor(sustained_checks_required=3)

    def _create_snapshot(self, t: float, p95: float, attempts: int, timeouts: int, exhaustions: int = 0):
        return {
            "timestamp": t,
            "latency_ms": {"p50": p95 * 0.8, "p95": p95, "p99": p95 * 1.2},
            "traffic": {"attempts_total": attempts, "unique_transactions_total": attempts},
            "outcomes": {
                "technical_timeouts": timeouts,
                "pool_exhaustion_errors": exhaustions,
                "approved": attempts - (timeouts + exhaustions)
            }
        }

    def test_silent_during_drift(self):
        # Durante o drift (255ms, 0 erros técnicos), o monitor tradicional não dispara
        for i in range(10):
            snap = self._create_snapshot(float(i), p95=255.0, attempts=100 * (i + 1), timeouts=0)
            res = self.monitor.evaluate(snap)
            self.assertFalse(res.triggered)

    def test_transient_spike_does_not_trigger(self):
        # 1 violação isolada de erro > 5% não deve disparar (regra de sustentabilidade)
        snap1 = self._create_snapshot(1.0, p95=50.0, attempts=100, timeouts=0)
        self.monitor.evaluate(snap1)

        # Spike de 10% de erros no segundo snapshot
        snap2 = self._create_snapshot(2.0, p95=50.0, attempts=200, timeouts=10)
        res = self.monitor.evaluate(snap2)
        self.assertFalse(res.triggered)

    def test_sustained_error_violations_trigger(self):
        # 3 violações consecutivas de erros > 5% devem disparar o Monitor A
        snap_base = self._create_snapshot(0.0, p95=50.0, attempts=100, timeouts=0)
        self.monitor.evaluate(snap_base)

        for i in range(1, 4):
            snap = self._create_snapshot(float(i), p95=100.0, attempts=100 + i * 100, timeouts=i * 15)
            res = self.monitor.evaluate(snap)

        self.assertTrue(res.triggered)
        self.assertIn("Monitor A", res.trigger_rule)

    def test_sustained_latency_violations_trigger(self):
        # 3 violações consecutivas de P95 > 1500ms devem disparar o Monitor B
        for i in range(3):
            snap = self._create_snapshot(float(i), p95=1600.0, attempts=100 * (i + 1), timeouts=0)
            res = self.monitor.evaluate(snap)

        self.assertTrue(res.triggered)
        self.assertIn("Monitor B", res.trigger_rule)

if __name__ == "__main__":
    unittest.main()
