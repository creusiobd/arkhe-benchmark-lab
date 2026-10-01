import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import yaml

from calibration.select_threshold import ScoredTrajectory, first_crossing, select_threshold
from contracts.evaluation_protocol import EvaluationProtocol
from contracts.ground_truth import TrajectoryGroundTruth
from contracts.observation import TrajectoryObservation
from scripts.audit_v05_shortcuts import audit
from scripts.generate_v05_dataset import generate


BASE_DIR = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = BASE_DIR / "configs" / "evaluation_protocol_v0.5.yaml"
DATASET_DIR = BASE_DIR / "datasets" / "v0.5_hard"


def load_jsonl(path, model):
    return [model.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


class TestV05Protocol(unittest.TestCase):
    def test_protocol_is_machine_valid_and_non_pooled(self):
        protocol = EvaluationProtocol.model_validate(yaml.safe_load(PROTOCOL_PATH.read_text(encoding="utf-8")))
        self.assertEqual(protocol.corpus.total_trajectories, 120)
        self.assertEqual(protocol.split.folds, 3)
        self.assertFalse(protocol.statistics.pool_repetitions)
        self.assertEqual(protocol.threshold.source, "validation_only")

    def test_dataset_counts_and_fixed_length(self):
        observations = load_jsonl(DATASET_DIR / "observations.jsonl", TrajectoryObservation)
        truths = load_jsonl(DATASET_DIR / "ground_truth" / "v0.5_labels.jsonl", TrajectoryGroundTruth)
        self.assertEqual(len(observations), 120)
        self.assertTrue(all(len(item.steps) == 5 for item in observations))
        self.assertEqual(
            Counter(item.ground_truth_class.value for item in truths),
            Counter({"benign": 48, "near_violation": 36, "violation": 36}),
        )
        self.assertEqual(len({item.trajectory_id for item in observations}), 120)

    def test_generation_is_byte_deterministic(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            manifest_a = generate(PROTOCOL_PATH, Path(first))
            manifest_b = generate(PROTOCOL_PATH, Path(second))
            self.assertEqual(manifest_a["files"], manifest_b["files"])

    def test_fold_isolation_and_complete_test_coverage(self):
        manifest = json.loads((DATASET_DIR / "split_manifest.json").read_text(encoding="utf-8"))
        seen_test_ids = []
        for fold in manifest["folds"].values():
            development = set(fold["development_ids"])
            validation = set(fold["validation_ids"])
            test = set(fold["test_ids"])
            self.assertFalse(development & validation)
            self.assertFalse(development & test)
            self.assertFalse(validation & test)
            self.assertEqual(len(test), 40)
            seen_test_ids.extend(test)
        self.assertEqual(len(seen_test_ids), 120)
        self.assertEqual(len(set(seen_test_ids)), 120)

    def test_shortcut_audit_passes(self):
        report = audit(DATASET_DIR)
        self.assertTrue(report["passed"])
        self.assertEqual(report["label_word_leakage_count"], 0)

    def test_rehearsal_is_bounded_and_paired_denominators_are_correct(self):
        report_path = BASE_DIR / "results" / "v0.5_offline" / "evaluation.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["claim_status"], "integration_only")
        for comparison in report["paired_task_a_negative_false_positive_decisions"].values():
            denominator = sum(comparison[key] for key in (
                "both_correct_a", "det1_correct_det2_wrong_b",
                "det1_wrong_det2_correct_c", "both_wrong_d",
            ))
            self.assertEqual(denominator, 84)
        for comparison in report["paired_task_a_positive_recall_decisions"].values():
            denominator = sum(comparison[key] for key in (
                "both_correct_a", "det1_correct_det2_wrong_b",
                "det1_wrong_det2_correct_c", "both_wrong_d",
            ))
            self.assertEqual(denominator, 36)

    def test_current_freeze_cannot_be_mislabeled_confirmatory(self):
        freeze_path = BASE_DIR / "freezes" / "v0.5_freeze.json"
        freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
        self.assertEqual(freeze["claim_eligibility"], "reproducibility_only")
        self.assertFalse(freeze["rules"]["confirmatory_claims_allowed"])
        manifest = json.loads(
            (BASE_DIR / "results" / "v0.5_frozen_offline" / "execution_manifest.json").read_text(encoding="utf-8")
        )
        evaluation = json.loads(
            (BASE_DIR / "results" / "v0.5_frozen_offline" / "evaluation.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["status"], "frozen_reproducibility_run")
        self.assertEqual(evaluation["claim_status"], "integration_only")


class TestV05Calibration(unittest.TestCase):
    def test_first_crossing_is_temporal(self):
        self.assertEqual(first_crossing([0.1, 0.7, 0.9], 0.7), 1)
        self.assertIsNone(first_crossing([0.1, 0.2], 0.3))

    def test_threshold_targets_recall_then_minimizes_fpr(self):
        items = [
            ScoredTrajectory("v1", "violation", [0.1, 0.8, 0.9], 2),
            ScoredTrajectory("v2", "violation", [0.2, 0.7, 0.95], 2),
            ScoredTrajectory("b1", "benign", [0.1, 0.2, 0.3]),
            ScoredTrajectory("n1", "near_violation", [0.1, 0.4, 0.5]),
        ]
        chosen = select_threshold(items, target_recall=1.0)
        self.assertEqual(chosen["status"], "target_met")
        self.assertEqual(chosen["threshold"], 0.7)
        self.assertEqual(chosen["fp"], 0)


if __name__ == "__main__":
    unittest.main()
