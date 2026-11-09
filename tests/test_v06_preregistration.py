import copy
import unittest
from pathlib import Path

import yaml
from pydantic import ValidationError

from contracts.preregistration import V06Preregistration
from scripts.validate_v06_preregistration import find_forbidden_design_artifacts, validate


BASE_DIR = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = BASE_DIR / "configs" / "evaluation_protocol_v0.6.yaml"


class TestV06Preregistration(unittest.TestCase):
    def load_raw(self):
        return yaml.safe_load(PROTOCOL_PATH.read_text(encoding="utf-8"))

    def test_design_stage_is_explicitly_non_confirmatory(self):
        protocol = V06Preregistration.model_validate(self.load_raw())
        self.assertEqual(protocol.stage, "design")
        self.assertEqual(protocol.claim_eligibility, "none")
        self.assertFalse(protocol.confirmatory_claims_allowed)
        self.assertFalse(protocol.freeze.frozen)

    def test_unresolved_decisions_block_freeze(self):
        protocol = V06Preregistration.model_validate(self.load_raw())
        unresolved = protocol.unresolved_for_freeze()
        self.assertIn("primary_hypothesis.primary_comparator", unresolved)
        self.assertIn("population.families", unresolved)
        self.assertIn("models.semantic_model_id", unresolved)
        self.assertIn("blinding.sealed_test_manifest_sha256", unresolved)
        with self.assertRaises(ValueError):
            protocol.assert_freezable()

    def test_design_cannot_enable_confirmatory_claims(self):
        raw = copy.deepcopy(self.load_raw())
        raw["confirmatory_claims_allowed"] = True
        with self.assertRaises(ValidationError):
            V06Preregistration.model_validate(raw)

    def test_v05_families_cannot_be_reused(self):
        raw = copy.deepcopy(self.load_raw())
        raw["population"]["families"] = [
            "indirect_prompt_injection",
            "memory_poisoning",
            "approval_bypass",
            "cross_agent_delegation",
        ]
        with self.assertRaises(ValidationError):
            V06Preregistration.model_validate(raw)

    def test_no_v06_data_or_results_exist_during_design(self):
        self.assertEqual(find_forbidden_design_artifacts(), [])
        report = validate(PROTOCOL_PATH)
        self.assertTrue(report["passed"])


if __name__ == "__main__":
    unittest.main()
