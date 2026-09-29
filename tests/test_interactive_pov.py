import unittest
import os
import tempfile
from run_interactive_pov import simulate_step, generate_pov_html_report

class TestInteractivePoVSandbox(unittest.TestCase):
    def test_nominal_step_calculation(self):
        state = simulate_step(
            phase_name="Nominal",
            step=1,
            total_steps=1,
            tps=120.0,
            service_time_ms=25.0,
            slots=30,
            fast_path=False,
            apm_alert=False
        )
        self.assertAlmostEqual(state["rho"], 0.10, places=2)
        self.assertLess(state["sentinel_score"], 30.0)
        self.assertFalse(state["apm_alert"])

    def test_chaos_drift_step_calculation(self):
        state = simulate_step(
            phase_name="Chaos Drift",
            step=1,
            total_steps=1,
            tps=120.0,
            service_time_ms=255.0,
            slots=30,
            fast_path=False,
            apm_alert=True
        )
        self.assertGreater(state["rho"], 1.0)
        self.assertEqual(state["sentinel_score"], 100.0)
        self.assertLess(state["ttc"], 2.0)

    def test_mitigated_step_restores_stability(self):
        state = simulate_step(
            phase_name="Mitigated",
            step=1,
            total_steps=1,
            tps=120.0,
            service_time_ms=180.0,
            slots=60,
            fast_path=True,
            apm_alert=False
        )
        # Fast path increases service rate by 1.6x, slots 60 -> rho drops significantly
        self.assertLess(state["rho"], 0.35)
        self.assertLess(state["sentinel_score"], 30.0)

    def test_html_report_generation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "test_report.html")
            results = [
                simulate_step("Nominal", 1, 1, 120.0, 25.0, 30),
                simulate_step("Drift", 1, 1, 120.0, 255.0, 30)
            ]
            summary = {
                "lead_time_s": 4.8,
                "mitigation_action": "Test Action",
                "audit_hash": "deadbeef123456",
                "timestamp": "2026-09-28 00:00:00Z"
            }
            generate_pov_html_report(results, summary, out_file)
            self.assertTrue(os.path.exists(out_file))
            with open(out_file, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("ARKHÉ CYBERNETIC RESILIENCE", content)
            self.assertIn("deadbeef123456", content)

if __name__ == "__main__":
    unittest.main()
