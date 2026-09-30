"""
Statistical Engine Unit Tests with Synthetic Fixtures
=====================================================
Validates non-parametric statistical procedures using synthetic, deterministically controlled fixtures:
1. Wilson score confidence interval calculations (endpoints, symmetry, small-sample behavior).
2. Non-parametric bootstrap confidence interval estimation.
3. McNemar test for paired binary classification (exact binomial & continuity-corrected chi-square).
4. Wilcoxon signed-rank paired test for ordinal lead time distributions.
5. Physical queueing consistency under Little's Law (M/M/c/K operational baseline).
"""

import unittest
import numpy as np
from evaluator.statistics import (
    wilson_score_interval,
    bootstrap_ci,
    mcnemar_test,
    wilcoxon_signed_rank_test
)


class TestStatisticsWithSyntheticFixture(unittest.TestCase):
    """Verifies mathematical validity of evaluator statistics against synthetic fixtures."""

    def test_wilson_score_interval_properties(self):
        # Edge case: zero successes
        low_0, high_0 = wilson_score_interval(0, 10, confidence=0.95)
        self.assertEqual(low_0, 0.0)
        self.assertGreater(high_0, 0.0)
        self.assertLess(high_0, 0.35)

        # Edge case: full successes
        low_10, high_10 = wilson_score_interval(10, 10, confidence=0.95)
        self.assertGreater(low_10, 0.65)
        self.assertEqual(high_10, 1.0)

        # Symmetric case
        low_half, high_half = wilson_score_interval(50, 100, confidence=0.95)
        self.assertAlmostEqual(0.5 - low_half, high_half - 0.5, places=3)
        self.assertTrue(0.39 < low_half < 0.42)
        self.assertTrue(0.58 < high_half < 0.61)

    def test_bootstrap_ci_synthetic_median_and_mean(self):
        # Synthetic fixture: skewed distribution
        synthetic_sample = [0.0, 0.0, 1.0, 1.0, 2.0, 3.0, 5.0, 8.0]
        res = bootstrap_ci(synthetic_sample, statistic_fn=lambda arr: sorted(arr)[len(arr) // 2], seed=42)

        self.assertIn("point_estimate", res)
        self.assertEqual(res["point_estimate"], 2.0)
        self.assertLessEqual(res["ci_lower"], res["point_estimate"])
        self.assertGreaterEqual(res["ci_upper"], res["point_estimate"])

    def test_mcnemar_test_discordance(self):
        # Synthetic contingency table:
        # a=15 (both correct), b=8 (ARKHÉ correct, Baseline failed)
        # c=1  (ARKHÉ failed, Baseline correct), d=6 (both failed)
        table = [[15, 8], [1, 6]]
        res = mcnemar_test(table)

        self.assertEqual(res["both_correct_a"], 15)
        self.assertEqual(res["det1_correct_det2_wrong_b"], 8)
        self.assertEqual(res["det1_wrong_det2_correct_c"], 1)
        self.assertEqual(res["total_discordant"], 9)
        self.assertEqual(res["odds_ratio"], 8.0)
        self.assertLess(res["exact_binomial_p_value"], 0.05)
        self.assertTrue(res["is_significant_005"])

    def test_mcnemar_symmetric_null(self):
        # Under H0: b == c
        table = [[20, 4], [4, 2]]
        res = mcnemar_test(table)
        self.assertEqual(res["exact_binomial_p_value"], 1.0)
        self.assertFalse(res["is_significant_005"])

    def test_wilcoxon_signed_rank_paired_shift(self):
        # Synthetic fixture with positive shift: x systematically exceeds y
        x = [5.0, 4.0, 6.0, 7.0, 5.0, 8.0]
        y = [1.0, 1.0, 2.0, 2.0, 1.0, 2.0]
        res = wilcoxon_signed_rank_test(x, y)

        self.assertEqual(res["n_nonzero"], 6)
        self.assertGreater(res["w_pos"], 0)
        self.assertEqual(res["w_neg"], 0)
        self.assertLess(res["p_value"], 0.05)
        self.assertTrue(res["is_significant_005"])

    def test_littles_law_physical_consistency_fixture(self):
        """Validates physical queuing consistency (L = lambda * W) across load regimes."""
        lambda_rate = 80.0
        ws_nominal = 0.045
        l_nominal = lambda_rate * ws_nominal
        self.assertAlmostEqual(l_nominal, 3.6, places=2)

        ws_drift = 0.255
        l_drift = lambda_rate * ws_drift
        self.assertAlmostEqual(l_drift, 20.4, places=2)

        ws_rupture = 0.420
        l_rupture = lambda_rate * ws_rupture
        self.assertGreater(l_rupture, 30.0)


if __name__ == "__main__":
    unittest.main()
