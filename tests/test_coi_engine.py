import unittest
from coi_engine import COIEngine, COIParameters

class TestCOIEngine(unittest.TestCase):
    def setUp(self):
        self.engine = COIEngine()

    def test_default_parameters(self):
        p = self.engine.p
        self.assertEqual(p.v_avg, 180.00)
        self.assertEqual(p.take_rate, 0.025)
        self.assertEqual(p.p_churn, 0.38)
        self.assertEqual(p.ltv_impact, 45.00)

    def test_zero_lost_txs(self):
        report = self.engine.calculate(delta_t_seconds=300.0, lost_unique_txs=0)
        self.assertEqual(report.direct_margin_loss_brl, 0.0)
        self.assertEqual(report.merchant_ltv_loss_brl, 0.0)
        self.assertEqual(report.total_coi_brl, 0.0)
        self.assertEqual(report.total_gmv_loss_brl, 0.0)

    def test_deterministic_coi_calculation(self):
        lost_txs = 1000
        report = self.engine.calculate(delta_t_seconds=300.0, lost_unique_txs=lost_txs)
        
        # Margem direta: 1000 * 180 * 0.025 = 4500.00
        self.assertEqual(report.direct_margin_loss_brl, 4500.00)
        # LTV Lojista: 1000 * (0.38 * 45) = 17100.00
        self.assertEqual(report.merchant_ltv_loss_brl, 17100.00)
        # COI Total: 4500 + 17100 = 21600.00
        self.assertEqual(report.total_coi_brl, 21600.00)
        # GMV Total: 1000 * 180 = 180000.00
        self.assertEqual(report.total_gmv_loss_brl, 180000.00)

    def test_confidence_interval_contains_mean(self):
        report = self.engine.calculate(delta_t_seconds=300.0, lost_unique_txs=500)
        low, high = report.confidence_interval_95_brl
        self.assertLess(low, report.total_coi_brl)
        self.assertGreater(high, report.total_coi_brl)

if __name__ == "__main__":
    unittest.main()
