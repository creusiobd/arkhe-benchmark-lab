"""
Tests for Dataset Isolation and Template Disjointness
=====================================================
Verifies that:
1. Observations contain zero ground truth labels or risk scores.
2. Templates in test set are disjoint from development templates.
3. Observation files match ground-truth IDs without cross-contamination.
"""

import os
import json
import unittest
from contracts.observation import TrajectoryObservation
from contracts.ground_truth import TrajectoryGroundTruth


class TestDatasetIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        cls.obs_dir = os.path.join(cls.root_dir, "datasets", "observations")
        cls.gt_dir = os.path.join(cls.root_dir, "datasets", "ground_truth")

    def test_observation_files_exist(self):
        for split in ["development", "validation", "test"]:
            fpath = os.path.join(self.obs_dir, f"{split}.jsonl")
            self.assertTrue(os.path.exists(fpath), f"Missing observation file: {fpath}")

    def test_ground_truth_files_exist(self):
        for split in ["development", "validation", "test"]:
            fpath = os.path.join(self.gt_dir, f"{split}_labels.jsonl")
            self.assertTrue(os.path.exists(fpath), f"Missing ground truth file: {fpath}")

    def test_no_leakage_in_raw_observation_jsonl(self):
        forbidden_keys = {
            "ground_truth_label",
            "ground_truth_class",
            "is_attack",
            "attack_vector",
            "violation_step_index",
            "drift_step_index",
            "mission_divergence_score",
            "context_contamination_flag",
            "accumulated_risk_score",
            "evaluator_rationale",
            "human_annotation_rationale",
        }
        for split in ["development", "validation", "test"]:
            fpath = os.path.join(self.obs_dir, f"{split}.jsonl")
            with open(fpath, "r", encoding="utf-8") as f:
                for line_idx, line in enumerate(f):
                    raw_data = json.loads(line)
                    # Test at trajectory level
                    found = forbidden_keys.intersection(raw_data.keys())
                    self.assertFalse(found, f"Leakage at {split}:{line_idx} keys: {found}")
                    # Test at each step
                    for s_idx, step in enumerate(raw_data.get("steps", [])):
                        found_step = forbidden_keys.intersection(step.keys())
                        self.assertFalse(found_step, f"Leakage at step {s_idx} in {split}:{line_idx}: {found_step}")

    def test_template_disjointness_between_dev_and_test(self):
        dev_gt_file = os.path.join(self.gt_dir, "development_labels.jsonl")
        test_gt_file = os.path.join(self.gt_dir, "test_labels.jsonl")

        dev_templates = set()
        with open(dev_gt_file, "r", encoding="utf-8") as f:
            for line in f:
                gt = TrajectoryGroundTruth.model_validate_json(line)
                dev_templates.add(gt.template_id)

        test_templates = set()
        with open(test_gt_file, "r", encoding="utf-8") as f:
            for line in f:
                gt = TrajectoryGroundTruth.model_validate_json(line)
                test_templates.add(gt.template_id)

        overlap = dev_templates.intersection(test_templates)
        self.assertEqual(len(overlap), 0, f"Template leakage detected between dev and test: {overlap}")

    def test_total_pilot_trajectories_count_is_30(self):
        total = 0
        for split in ["development", "validation", "test"]:
            fpath = os.path.join(self.obs_dir, f"{split}.jsonl")
            with open(fpath, "r", encoding="utf-8") as f:
                total += sum(1 for _ in f)
        self.assertEqual(total, 30, f"Pilot dataset must have exactly 30 trajectories, got {total}")


if __name__ == "__main__":
    unittest.main()
