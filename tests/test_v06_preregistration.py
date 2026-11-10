import copy
import hashlib
import json
import tempfile
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

    def build_manifest(self, raw):
        cases = []
        for family in raw["population"]["families"]:
            for case_class, count in raw["population"]["class_counts_per_family"].items():
                for index in range(count):
                    case_id = f"{family}-{case_class}-{index:02d}"
                    cases.append(
                        {
                            "case_id": case_id,
                            "family": family,
                            "case_class": case_class,
                            "content_sha256": hashlib.sha256(case_id.encode()).hexdigest(),
                        }
                    )
        return {
            "protocol_id": raw["protocol_id"],
            "protocol_version": raw["version"],
            "cases": cases,
        }

    def write_freeze_candidate(self, root, raw, manifest):
        manifest_path = root / "private_manifest.json"
        manifest_bytes = json.dumps(
            manifest, sort_keys=True, separators=(",", ":")
        ).encode()
        manifest_path.write_bytes(manifest_bytes)
        raw["blinding"]["custodian_identity"] = "independent-custodian"
        raw["blinding"]["sealed_test_manifest_sha256"] = hashlib.sha256(
            manifest_bytes
        ).hexdigest()
        raw["freeze"]["approver"] = "independent-approver"
        protocol_path = root / "protocol.yaml"
        protocol_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
        return protocol_path, manifest_path

    def test_design_stage_is_explicitly_non_confirmatory(self):
        protocol = V06Preregistration.model_validate(self.load_raw())
        self.assertEqual(protocol.stage, "design")
        self.assertEqual(protocol.claim_eligibility, "none")
        self.assertFalse(protocol.confirmatory_claims_allowed)
        self.assertFalse(protocol.freeze.frozen)

    def test_unresolved_decisions_block_freeze(self):
        protocol = V06Preregistration.model_validate(self.load_raw())
        unresolved = protocol.unresolved_for_freeze()
        self.assertNotIn("primary_hypothesis.primary_comparator", unresolved)
        self.assertNotIn("population.families", unresolved)
        self.assertNotIn("models.semantic_model_id", unresolved)
        self.assertNotIn("statistics.missing_data_rule", unresolved)
        self.assertNotIn("statistics.stopping_rule", unresolved)
        self.assertIn("blinding.custodian_identity", unresolved)
        self.assertIn("blinding.sealed_test_manifest_sha256", unresolved)
        self.assertIn("freeze.approver", unresolved)
        with self.assertRaises(ValueError):
            protocol.assert_freezable()

    def test_scientific_design_decisions_are_predeclared(self):
        protocol = V06Preregistration.model_validate(self.load_raw())
        self.assertEqual(protocol.primary_hypothesis.primary_comparator, "semantic_event")
        self.assertEqual(protocol.primary_hypothesis.minimum_effect_percentage_points, 15.0)
        self.assertEqual(protocol.population.source_type, "independent_synthetic")
        self.assertEqual(protocol.population.total_trajectories, 160)
        self.assertEqual(protocol.population.trajectories_per_family, 40)
        self.assertEqual(
            protocol.population.class_counts_per_family,
            {"benign": 16, "near_violation": 12, "violation": 12},
        )
        self.assertEqual(len(protocol.population.families), 4)
        self.assertEqual(protocol.split.strategy, "sealed_external_test")
        self.assertEqual(protocol.split.calibration_source, "historical_validation_only")
        self.assertEqual(protocol.models.semantic_model_id, "gpt-6.1-sol")

    def test_population_allocation_must_match_declared_total(self):
        raw = copy.deepcopy(self.load_raw())
        raw["population"]["trajectories_per_family"] = 39
        with self.assertRaises(ValidationError):
            V06Preregistration.model_validate(raw)

    def test_population_must_keep_exactly_four_unique_families(self):
        raw = copy.deepcopy(self.load_raw())
        raw["population"]["families"].append("fifth_family")
        raw["population"]["total_trajectories"] = 200
        with self.assertRaises(ValidationError):
            V06Preregistration.model_validate(raw)

    def test_class_allocation_must_match_family_total(self):
        raw = copy.deepcopy(self.load_raw())
        raw["population"]["class_counts_per_family"]["benign"] = 15
        with self.assertRaises(ValidationError):
            V06Preregistration.model_validate(raw)

    def test_manifest_digest_rejects_placeholders_and_malformed_values(self):
        for invalid_digest in ("placeholder", "0" * 63, "A" * 64):
            raw = copy.deepcopy(self.load_raw())
            raw["blinding"]["sealed_test_manifest_sha256"] = invalid_digest
            with self.assertRaises(ValidationError):
                V06Preregistration.model_validate(raw)

    def test_freeze_gate_verifies_private_manifest_digest_and_distribution(self):
        raw = copy.deepcopy(self.load_raw())
        manifest = self.build_manifest(raw)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol_path, manifest_path = self.write_freeze_candidate(
                root, raw, manifest
            )
            report = validate(
                protocol_path,
                require_freezable=True,
                manifest_path=manifest_path,
                base_dir=root,
            )
        self.assertTrue(report["passed"], report["errors"])
        self.assertTrue(report["manifest_verified"])

    def test_freeze_gate_rejects_unbalanced_private_manifest(self):
        raw = copy.deepcopy(self.load_raw())
        manifest = self.build_manifest(raw)
        manifest["cases"][0]["family"] = raw["population"]["families"][1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol_path, manifest_path = self.write_freeze_candidate(
                root, raw, manifest
            )
            report = validate(
                protocol_path,
                require_freezable=True,
                manifest_path=manifest_path,
                base_dir=root,
            )
        self.assertFalse(report["passed"])
        self.assertFalse(report["manifest_verified"])
        self.assertTrue(
            any("must contain exactly 40 cases" in error for error in report["errors"])
        )

    def test_freeze_gate_rejects_manifest_modified_after_sealing(self):
        raw = copy.deepcopy(self.load_raw())
        manifest = self.build_manifest(raw)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol_path, manifest_path = self.write_freeze_candidate(
                root, raw, manifest
            )
            manifest_path.write_bytes(manifest_path.read_bytes() + b"\n")
            report = validate(
                protocol_path,
                require_freezable=True,
                manifest_path=manifest_path,
                base_dir=root,
            )
        self.assertFalse(report["passed"])
        self.assertIn(
            "sealed manifest SHA-256 does not match the protocol commitment",
            report["errors"],
        )

    def test_freeze_gate_rejects_manifest_for_another_protocol(self):
        raw = copy.deepcopy(self.load_raw())
        manifest = self.build_manifest(raw)
        manifest["protocol_id"] = "another-protocol"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol_path, manifest_path = self.write_freeze_candidate(
                root, raw, manifest
            )
            report = validate(
                protocol_path,
                require_freezable=True,
                manifest_path=manifest_path,
                base_dir=root,
            )
        self.assertFalse(report["passed"])
        self.assertIn(
            "sealed manifest protocol_id does not match the protocol",
            report["errors"],
        )

    def test_freeze_gate_rejects_manifest_for_another_protocol_version(self):
        raw = copy.deepcopy(self.load_raw())
        manifest = self.build_manifest(raw)
        manifest["protocol_version"] = "0.6.0-other"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol_path, manifest_path = self.write_freeze_candidate(
                root, raw, manifest
            )
            report = validate(
                protocol_path,
                require_freezable=True,
                manifest_path=manifest_path,
                base_dir=root,
            )
        self.assertFalse(report["passed"])
        self.assertIn(
            "sealed manifest protocol_version does not match the protocol",
            report["errors"],
        )

    def test_freeze_gate_rejects_duplicate_case_content(self):
        raw = copy.deepcopy(self.load_raw())
        manifest = self.build_manifest(raw)
        manifest["cases"][1]["content_sha256"] = manifest["cases"][0][
            "content_sha256"
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol_path, manifest_path = self.write_freeze_candidate(
                root, raw, manifest
            )
            report = validate(
                protocol_path,
                require_freezable=True,
                manifest_path=manifest_path,
                base_dir=root,
            )
        self.assertFalse(report["passed"])
        self.assertTrue(
            any("duplicate content_sha256" in error for error in report["errors"])
        )

    def test_freeze_gate_requires_the_private_manifest(self):
        raw = copy.deepcopy(self.load_raw())
        raw["blinding"]["custodian_identity"] = "independent-custodian"
        raw["blinding"]["sealed_test_manifest_sha256"] = "0" * 64
        raw["freeze"]["approver"] = "independent-approver"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol_path = root / "protocol.yaml"
            protocol_path.write_text(
                yaml.safe_dump(raw, sort_keys=False), encoding="utf-8"
            )
            report = validate(
                protocol_path, require_freezable=True, base_dir=root
            )
        self.assertFalse(report["passed"])
        self.assertFalse(report["manifest_verified"])
        self.assertIn(
            "--manifest is required when --require-freezable is used",
            report["errors"],
        )

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
