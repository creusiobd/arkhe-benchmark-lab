"""
ARKHÉ Agent Boundary Defense Benchmark — Deterministic Reproduction Tests
==========================================================================
Unit and regression tests verifying deterministic dataset generation:
1. Identical generation parameters produce identical trajectory IDs.
2. Varying seed, split, template, class, or index produces distinct IDs.
3. IDs are opaque (traj_<16 hex>), containing zero class or family words.
4. Absence of collisions across the entire generated benchmark blueprints.
5. Exact ID correspondence between observations and sealed ground truth.
6. Ordering and serialization stability across multiple dumps.
7. Hashes are identical across two independent isolated generations.
8. Hashes diverge when an input parameter (e.g., seed) is changed.
9. Manifest captures commit, dirty status, config hash, seed, and dependency versions.
10. Generation into temporary directories preserves tracked and legacy datasets.

All fixtures herein are synthetic and used strictly for reproducibility validation.
Determinism tests do not serve as scientific evidence of detection performance.
"""

import os
import sys
import json
import tempfile
import unittest
from typing import Dict, Any

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from scripts.generate_hard_dataset import (
    compute_deterministic_trajectory_id,
    compute_file_sha256,
    generate_hard_dataset,
    get_git_provenance,
    get_exact_dependencies,
    HARD_SCENARIO_BLUEPRINTS,
    DEFAULT_RANDOM_SEED
)
from contracts.observation import TrajectoryObservation
from contracts.ground_truth import TrajectoryGroundTruth


class TestDeterministicReproduction(unittest.TestCase):

    def test_identical_parameters_produce_identical_ids(self):
        """1. Calling compute_deterministic_trajectory_id with identical inputs yields identical IDs."""
        id1 = compute_deterministic_trajectory_id(
            seed=20260930, split="development", template_id="dev_pi_01",
            ground_truth_class="violation", trajectory_index=0
        )
        id2 = compute_deterministic_trajectory_id(
            seed=20260930, split="development", template_id="dev_pi_01",
            ground_truth_class="violation", trajectory_index=0
        )
        self.assertEqual(id1, id2)

    def test_varying_parameters_produce_different_ids(self):
        """2. Changing seed, split, template, class, or index produces distinct IDs."""
        base_kwargs = {
            "seed": 20260930,
            "split": "development",
            "template_id": "tmpl_alpha",
            "ground_truth_class": "benign",
            "trajectory_index": 0
        }
        base_id = compute_deterministic_trajectory_id(**base_kwargs)

        variations = [
            compute_deterministic_trajectory_id(**{**base_kwargs, "seed": 99999999}),
            compute_deterministic_trajectory_id(**{**base_kwargs, "split": "validation"}),
            compute_deterministic_trajectory_id(**{**base_kwargs, "template_id": "tmpl_beta"}),
            compute_deterministic_trajectory_id(**{**base_kwargs, "ground_truth_class": "violation"}),
            compute_deterministic_trajectory_id(**{**base_kwargs, "trajectory_index": 1}),
        ]

        for var_id in variations:
            self.assertNotEqual(base_id, var_id, f"ID variation collision: {base_id} == {var_id}")

        # All variations mutually distinct
        all_ids = [base_id] + variations
        self.assertEqual(len(all_ids), len(set(all_ids)))

    def test_ids_are_opaque_and_contain_no_class_or_family_leakage(self):
        """3. IDs must be strictly traj_<16 hex chars>, with zero leak of class or family names."""
        tid = compute_deterministic_trajectory_id(
            seed=20260930, split="development", template_id="dev_pi_benign",
            ground_truth_class="near_violation", trajectory_index=3
        )
        self.assertTrue(tid.startswith("traj_"), f"ID must start with traj_, got {tid}")
        hex_part = tid[5:]
        self.assertEqual(len(hex_part), 16, f"Hex digest must be exactly 16 characters, got {len(hex_part)}")
        self.assertTrue(all(c in "0123456789abcdef" for c in hex_part), f"Digest must be pure hex: {hex_part}")

        forbidden_words = [
            "benign", "violation", "near", "dev", "val", "test",
            "injection", "secret", "exposure", "scope", "prompt"
        ]
        for w in forbidden_words:
            self.assertNotIn(w, tid.lower(), f"Opaque ID contains forbidden lexical leak '{w}': {tid}")

    def test_zero_collisions_in_blueprint_dataset(self):
        """4. Verify zero ID collisions when generating trajectory IDs for all 50 blueprints."""
        seen_ids = set()
        splits_data = {"development": [], "validation": [], "test": []}
        for skey, sdata in HARD_SCENARIO_BLUEPRINTS.items():
            splits_data[sdata["split"]].append((skey, sdata))

        for split_name in ["development", "validation", "test"]:
            scenarios = sorted(splits_data[split_name], key=lambda x: x[0])
            for idx, (skey, sdata) in enumerate(scenarios):
                tid = compute_deterministic_trajectory_id(
                    seed=DEFAULT_RANDOM_SEED,
                    split=split_name,
                    template_id=skey,
                    ground_truth_class=sdata["label"].value,
                    trajectory_index=idx
                )
                self.assertNotIn(tid, seen_ids, f"Collision detected for ID: {tid}")
                seen_ids.add(tid)

        self.assertEqual(len(seen_ids), 50)

    def test_exact_id_correspondence_between_observations_and_ground_truth(self):
        """5. In every generated split, every observation trajectory_id matches the ground truth trajectory_id."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            generate_hard_dataset(output_dir=tmp_dir, seed=20260930, emit_report=False)

            for split in ["development", "validation", "test"]:
                obs_path = os.path.join(tmp_dir, "observations", f"{split}.jsonl")
                gt_path = os.path.join(tmp_dir, "ground_truth", f"{split}_labels.jsonl")

                obs_ids = []
                with open(obs_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            obs = TrajectoryObservation.model_validate_json(line)
                            obs_ids.append(obs.trajectory_id)

                gt_ids = []
                with open(gt_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            gt = TrajectoryGroundTruth.model_validate_json(line)
                            gt_ids.append(gt.trajectory_id)

                self.assertEqual(obs_ids, gt_ids, f"Mismatch in {split} IDs between observations and GT")
                self.assertEqual(len(obs_ids), len(set(obs_ids)), f"Duplicate ID in split {split}")

    def test_ordering_and_serialization_stability(self):
        """6. Re-serializing dataset files produces identical line-by-line byte representations."""
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            generate_hard_dataset(output_dir=d1, seed=20260930, emit_report=False)
            generate_hard_dataset(output_dir=d2, seed=20260930, emit_report=False)

            for rel_file in [
                "observations/development.jsonl",
                "ground_truth/development_labels.jsonl",
                "templates/templates_catalog.json"
            ]:
                p1 = os.path.join(d1, rel_file)
                p2 = os.path.join(d2, rel_file)
                with open(p1, "rb") as f1, open(p2, "rb") as f2:
                    self.assertEqual(f1.read(), f2.read(), f"File content mismatch: {rel_file}")

    def test_independent_generations_produce_identical_dataset_hashes(self):
        """7. Two independent executions in separate temp dirs produce identical SHA-256 file hashes."""
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            m1 = generate_hard_dataset(output_dir=d1, seed=20260930, emit_report=False)
            m2 = generate_hard_dataset(output_dir=d2, seed=20260930, emit_report=False)

            h1 = m1["deterministic_metadata"]["dataset_file_hashes"]
            h2 = m2["deterministic_metadata"]["dataset_file_hashes"]
            self.assertEqual(h1, h2, "File hashes diverged between independent runs with identical seed")
            self.assertEqual(len(h1), 9, "Expected 9 deterministic dataset files")

    def test_hash_divergence_when_seed_changes(self):
        """8. Changing the random seed must produce different file hashes."""
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            m1 = generate_hard_dataset(output_dir=d1, seed=20260930, emit_report=False)
            m2 = generate_hard_dataset(output_dir=d2, seed=99999999, emit_report=False)

            h1 = m1["deterministic_metadata"]["dataset_file_hashes"]
            h2 = m2["deterministic_metadata"]["dataset_file_hashes"]
            # Observations and GT hashes must differ
            self.assertNotEqual(h1["observations/development.jsonl"], h2["observations/development.jsonl"])
            self.assertNotEqual(h1["ground_truth/development_labels.jsonl"], h2["ground_truth/development_labels.jsonl"])

    def test_manifest_records_provenance_correctly(self):
        """9. Manifest captures commit, dirty status, config hash, seed, and environment."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            generate_hard_dataset(output_dir=tmp_dir, seed=20260930, emit_report=False)
            m_path = os.path.join(tmp_dir, "generation_manifest.json")
            self.assertTrue(os.path.exists(m_path))

            with open(m_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            det = manifest.get("deterministic_metadata", {})
            self.assertEqual(det.get("random_seed"), 20260930)
            self.assertEqual(det.get("generator_version"), "0.4.0")
            self.assertIn("source_commit", det)
            self.assertIn("worktree_is_dirty", det)
            self.assertIn("environment", det)
            self.assertIn("dependencies", det)
            self.assertIn("pydantic", det["dependencies"])
            self.assertIn("dataset_file_hashes", det)

            exec_meta = manifest.get("execution_run_metadata", {})
            self.assertIn("generated_at_utc", exec_meta)
            self.assertIn("execution_duration_seconds", exec_meta)

    def test_temporary_generation_preserves_tracked_datasets(self):
        """10. Generating into a temporary directory never touches or overwrites tracked repository datasets."""
        v03_dev_path = os.path.join(BASE_DIR, "datasets", "v0.3", "observations", "development.jsonl")
        self.assertTrue(os.path.exists(v03_dev_path))
        v03_hash_before = compute_file_sha256(v03_dev_path)

        with tempfile.TemporaryDirectory() as tmp_dir:
            generate_hard_dataset(output_dir=tmp_dir, seed=20260930, emit_report=False)

        v03_hash_after = compute_file_sha256(v03_dev_path)
        self.assertEqual(v03_hash_before, v03_hash_after, "Legacy v0.3 dataset was contaminated by generator!")


if __name__ == "__main__":
    unittest.main()
