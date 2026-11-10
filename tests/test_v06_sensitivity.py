import unittest
from pathlib import Path

import yaml

from contracts.preregistration import V06Preregistration
from scripts.analyze_v06_sensitivity import (
    build_report,
    exact_mcnemar_power,
    minimum_sample_size,
)

BASE_DIR = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = BASE_DIR / "configs" / "evaluation_protocol_v0.6.yaml"


class TestV06Sensitivity(unittest.TestCase):
    def load_protocol(self):
        return V06Preregistration.model_validate(
            yaml.safe_load(PROTOCOL_PATH.read_text(encoding="utf-8"))
        )

    def test_selected_design_is_adequate_at_predeclared_discordance(self):
        report = build_report(self.load_protocol())
        self.assertEqual(report["sample_size"], 200)
        self.assertEqual(report["design_discordance_rate"], 0.50)
        self.assertTrue(report["design_adequate"])
        self.assertAlmostEqual(report["design_power"], 0.836436, places=5)

    def test_sensitivity_discloses_weaker_high_discordance_scenario(self):
        report = build_report(self.load_protocol())
        high_discordance = next(
            scenario
            for scenario in report["scenarios"]
            if scenario["discordance_rate"] == 0.60
        )
        self.assertAlmostEqual(high_discordance["power"], 0.761079, places=5)
        self.assertEqual(high_discordance["minimum_n_for_target_power"], 219)

    def test_160_cases_would_not_meet_target_at_design_discordance(self):
        power = exact_mcnemar_power(160, 0.15, 0.50, 0.05)
        self.assertAlmostEqual(power, 0.738376, places=5)
        self.assertLess(power, 0.80)

    def test_minimum_n_at_design_discordance_is_183(self):
        self.assertEqual(minimum_sample_size(0.15, 0.50, 0.80, 0.05), 183)

    def test_effect_cannot_exceed_total_discordance(self):
        with self.assertRaises(ValueError):
            exact_mcnemar_power(200, 0.15, 0.10, 0.05)


if __name__ == "__main__":
    unittest.main()
