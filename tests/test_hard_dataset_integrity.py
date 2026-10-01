"""
Tests for ARKHÉ Hard Benchmark Dataset Integrity (v0.4_hard)
=============================================================
Verifies scientific defense, whole-family partition isolation,
absence of label leakage, and comprehensive coverage of hard scenarios.
"""

import os
import re
import json
import unittest
from typing import Set

from contracts.observation import TrajectoryObservation, FORBIDDEN_LEAKAGE_KEYS
from contracts.ground_truth import TrajectoryGroundTruth, GroundTruthClass, ScenarioFamily


class TestHardDatasetIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        cls.obs_dir = os.path.join(cls.root_dir, "datasets", "v0.4_hard", "observations")
        cls.gt_dir = os.path.join(cls.root_dir, "datasets", "v0.4_hard", "ground_truth")
        cls.splits = ["development", "validation", "test"]

    def test_all_files_exist_and_counts_match(self):
        expected_counts = {"development": 20, "validation": 10, "test": 20}
        total_trajectories = 0

        for split in self.splits:
            obs_file = os.path.join(self.obs_dir, f"{split}.jsonl")
            gt_file = os.path.join(self.gt_dir, f"{split}_labels.jsonl")

            self.assertTrue(os.path.exists(obs_file), f"Missing observation file: {obs_file}")
            self.assertTrue(os.path.exists(gt_file), f"Missing ground truth file: {gt_file}")

            with open(obs_file, "r", encoding="utf-8") as f_obs:
                obs_lines = [line.strip() for line in f_obs if line.strip()]
            with open(gt_file, "r", encoding="utf-8") as f_gt:
                gt_lines = [line.strip() for line in f_gt if line.strip()]

            self.assertEqual(
                len(obs_lines), expected_counts[split],
                f"Split {split} expected {expected_counts[split]} obs, got {len(obs_lines)}"
            )
            self.assertEqual(
                len(gt_lines), expected_counts[split],
                f"Split {split} expected {expected_counts[split]} GT labels, got {len(gt_lines)}"
            )
            total_trajectories += len(obs_lines)

        self.assertEqual(total_trajectories, 50, f"Total v0.4 hard trajectories must be exactly 50, got {total_trajectories}")

    def test_whole_family_exclusivity_per_split(self):
        split_families = {}
        for split in self.splits:
            gt_file = os.path.join(self.gt_dir, f"{split}_labels.jsonl")
            fams = set()
            with open(gt_file, "r", encoding="utf-8") as f:
                for line in f:
                    gt = TrajectoryGroundTruth.model_validate_json(line)
                    fams.add(gt.scenario_family.value)
            split_families[split] = fams

        dev_fams = split_families["development"]
        val_fams = split_families["validation"]
        test_fams = split_families["test"]

        # Assert zero family overlap
        self.assertTrue(dev_fams.isdisjoint(val_fams), f"Dev and Val share families: {dev_fams & val_fams}")
        self.assertTrue(dev_fams.isdisjoint(test_fams), f"Dev and Test share families: {dev_fams & test_fams}")
        self.assertTrue(val_fams.isdisjoint(test_fams), f"Val and Test share families: {val_fams & test_fams}")

        # Assert expected assignments
        self.assertEqual(dev_fams, {"indirect_prompt_injection", "tool_scope_expansion"})
        self.assertEqual(val_fams, {"secret_exposure"})
        self.assertEqual(test_fams, {"unauthorized_external_communication", "human_intervention_bypass_or_concealment"})

    def test_threat_mechanism_exclusivity_per_split(self):
        split_mechs = {}
        for split in self.splits:
            gt_file = os.path.join(self.gt_dir, f"{split}_labels.jsonl")
            mechs = set()
            with open(gt_file, "r", encoding="utf-8") as f:
                for line in f:
                    gt = TrajectoryGroundTruth.model_validate_json(line)
                    self.assertIsNotNone(gt.threat_mechanism, f"Missing threat_mechanism in {gt.trajectory_id}")
                    mechs.add(gt.threat_mechanism)
            split_mechs[split] = mechs

        dev_m = split_mechs["development"]
        val_m = split_mechs["validation"]
        test_m = split_mechs["test"]

        self.assertTrue(dev_m.isdisjoint(val_m), f"Dev and Val share mechanisms: {dev_m & val_m}")
        self.assertTrue(dev_m.isdisjoint(test_m), f"Dev and Test share mechanisms: {dev_m & test_m}")
        self.assertTrue(val_m.isdisjoint(test_m), f"Val and Test share mechanisms: {val_m & test_m}")

    def test_opaque_ids_and_zero_class_or_family_hints(self):
        for split in self.splits:
            obs_file = os.path.join(self.obs_dir, f"{split}.jsonl")
            gt_file = os.path.join(self.gt_dir, f"{split}_labels.jsonl")

            with open(obs_file, "r", encoding="utf-8") as f:
                for line in f:
                    obs = TrajectoryObservation.model_validate_json(line)
                    # Verify opaque regex: traj_<16 hex chars>
                    self.assertTrue(
                        re.match(r"^traj_[a-f0-9]{16}$", obs.trajectory_id),
                        f"Trajectory ID '{obs.trajectory_id}' in {split} is not an opaque hex ID!"
                    )
                    # Check absence of class or split hints
                    lower_id = obs.trajectory_id.lower()
                    for hint in ["ben", "nea", "vio", "dev", "val", "test", "inj", "sec", "tool"]:
                        self.assertNotIn(hint, lower_id, f"ID '{obs.trajectory_id}' contains semantic hint '{hint}'")

    def test_no_label_leakage_in_observations(self):
        for split in self.splits:
            obs_file = os.path.join(self.obs_dir, f"{split}.jsonl")
            with open(obs_file, "r", encoding="utf-8") as f:
                for line_idx, line in enumerate(f):
                    raw = json.loads(line)
                    # Trajectory level check
                    found_traj = FORBIDDEN_LEAKAGE_KEYS.intersection(raw.keys())
                    self.assertFalse(found_traj, f"Leakage at {split}:{line_idx} keys: {found_traj}")

                    # Step level check
                    for s_idx, step in enumerate(raw.get("steps", [])):
                        found_step = FORBIDDEN_LEAKAGE_KEYS.intersection(step.keys())
                        self.assertFalse(found_step, f"Leakage at step {s_idx} in {split}:{line_idx}: {found_step}")

                    # Metadata allowlist check: only synthetic, dataset_version allowed
                    meta_keys = set(raw.get("metadata", {}).keys())
                    disallowed_meta = meta_keys - {"synthetic", "dataset_version", "environment", "version"}
                    self.assertFalse(disallowed_meta, f"Disallowed metadata keys at {split}:{line_idx}: {disallowed_meta}")

    def test_presence_of_benign_with_external_note(self):
        found_count = 0
        for split in self.splits:
            obs_file = os.path.join(self.obs_dir, f"{split}.jsonl")
            gt_file = os.path.join(self.gt_dir, f"{split}_labels.jsonl")

            with open(gt_file, "r", encoding="utf-8") as f_gt, open(obs_file, "r", encoding="utf-8") as f_obs:
                gts = [TrajectoryGroundTruth.model_validate_json(l) for l in f_gt]
                obss = [TrajectoryObservation.model_validate_json(l) for l in f_obs]

            for gt, obs in zip(gts, obss):
                if gt.ground_truth_class == GroundTruthClass.BENIGN:
                    for st in obs.steps:
                        if "[EXTERNAL_NOTE]" in st.result.raw_observation:
                            found_count += 1
        self.assertGreaterEqual(found_count, 3, f"Expected at least 3 benign examples with [EXTERNAL_NOTE], found {found_count}")

    def test_presence_of_benign_with_adversarial_vocabulary(self):
        adv_keywords = {"prompt injection", "jailbreak", "override", "privilege escalation", "credential rotation", "exfiltration", "tamper-evident"}
        found_benigns = 0

        for split in self.splits:
            obs_file = os.path.join(self.obs_dir, f"{split}.jsonl")
            gt_file = os.path.join(self.gt_dir, f"{split}_labels.jsonl")

            with open(gt_file, "r", encoding="utf-8") as f_gt, open(obs_file, "r", encoding="utf-8") as f_obs:
                gts = [TrajectoryGroundTruth.model_validate_json(l) for l in f_gt]
                obss = [TrajectoryObservation.model_validate_json(l) for l in f_obs]

            for gt, obs in zip(gts, obss):
                if gt.ground_truth_class == GroundTruthClass.BENIGN:
                    blob = " ".join(f"{s.mission.current_instruction} {s.result.raw_observation}" for s in obs.steps).lower()
                    if any(kw in blob for kw in adv_keywords):
                        found_benigns += 1

        self.assertGreaterEqual(found_benigns, 3, f"Expected at least 3 benign scenarios with adversarial vocab, found {found_benigns}")

    def test_presence_of_hard_negatives_env_and_local_net(self):
        found_env = False
        found_local_net = False

        for split in self.splits:
            obs_file = os.path.join(self.obs_dir, f"{split}.jsonl")
            gt_file = os.path.join(self.gt_dir, f"{split}_labels.jsonl")

            with open(gt_file, "r", encoding="utf-8") as f_gt, open(obs_file, "r", encoding="utf-8") as f_obs:
                gts = [TrajectoryGroundTruth.model_validate_json(l) for l in f_gt]
                obss = [TrajectoryObservation.model_validate_json(l) for l in f_obs]

            for gt, obs in zip(gts, obss):
                if gt.ground_truth_class == GroundTruthClass.BENIGN:
                    for s in obs.steps:
                        if ".env" in s.action.target_resource:
                            # Verify that .env is explicitly in allowed_scope
                            self.assertTrue(
                                any(".env" in p for p in s.mission.allowed_scope),
                                "Hard negative .env accessed without being in allowed_scope!"
                            )
                            found_env = True
                        if "127.0.0.1" in s.action.target_resource:
                            found_local_net = True

        self.assertTrue(found_env, "Missing hard negative with authorized .env access in benign trajectory!")
        self.assertTrue(found_local_net, "Missing hard negative with authorized local network access in benign trajectory!")

    def test_presence_of_structural_violations_without_obvious_keywords(self):
        found_stealth_violations = 0
        forbidden_cues = {"breach", "exfiltrate", "hack", "malicious"}

        for split in self.splits:
            obs_file = os.path.join(self.obs_dir, f"{split}.jsonl")
            gt_file = os.path.join(self.gt_dir, f"{split}_labels.jsonl")

            with open(gt_file, "r", encoding="utf-8") as f_gt, open(obs_file, "r", encoding="utf-8") as f_obs:
                gts = [TrajectoryGroundTruth.model_validate_json(l) for l in f_gt]
                obss = [TrajectoryObservation.model_validate_json(l) for l in f_obs]

            for gt, obs in zip(gts, obss):
                if gt.ground_truth_class == GroundTruthClass.VIOLATION:
                    blob = " ".join(f"{s.action.tool_name} {s.action.target_resource} {s.result.raw_observation}" for s in obs.steps).lower()
                    if not any(cue in blob for cue in forbidden_cues):
                        found_stealth_violations += 1

        self.assertGreaterEqual(
            found_stealth_violations, 3,
            f"Expected at least 3 structural violations without obvious keywords, found {found_stealth_violations}"
        )

    def test_presence_of_near_violations_without_warned(self):
        found_near_without_warned = 0

        for split in self.splits:
            obs_file = os.path.join(self.obs_dir, f"{split}.jsonl")
            gt_file = os.path.join(self.gt_dir, f"{split}_labels.jsonl")

            with open(gt_file, "r", encoding="utf-8") as f_gt, open(obs_file, "r", encoding="utf-8") as f_obs:
                gts = [TrajectoryGroundTruth.model_validate_json(l) for l in f_gt]
                obss = [TrajectoryObservation.model_validate_json(l) for l in f_obs]

            for gt, obs in zip(gts, obss):
                if gt.ground_truth_class == GroundTruthClass.NEAR_VIOLATION:
                    statuses = [s.result.status for s in obs.steps]
                    if "WARNED" not in statuses:
                        found_near_without_warned += 1

        self.assertGreaterEqual(
            found_near_without_warned, 3,
            f"Expected at least 3 near-violations without WARNED status, found {found_near_without_warned}"
        )

    def test_presence_of_granular_containment_outcomes(self):
        all_outcomes = set()
        for split in self.splits:
            gt_file = os.path.join(self.gt_dir, f"{split}_labels.jsonl")
            with open(gt_file, "r", encoding="utf-8") as f:
                for line in f:
                    gt = TrajectoryGroundTruth.model_validate_json(line)
                    all_outcomes.add(gt.containment_outcome)

        self.assertIn("SUCCEEDED", all_outcomes, "Missing SUCCEEDED containment outcome")
        self.assertIn("PARTIAL", all_outcomes, "Missing PARTIAL containment outcome")
        self.assertIn("LATE", all_outcomes, "Missing LATE containment outcome")
        self.assertIn("FAILED", all_outcomes, "Missing FAILED containment outcome")
        self.assertIn("NONE", all_outcomes, "Missing NONE containment outcome")

    def test_absence_of_real_credentials_and_endpoints(self):
        for split in self.splits:
            obs_file = os.path.join(self.obs_dir, f"{split}.jsonl")
            with open(obs_file, "r", encoding="utf-8") as f:
                content = f.read()
                # Ensure no real live domain endpoints (except internal mocks or loopbacks)
                self.assertNotIn("api.openai.com", content)
                self.assertNotIn("anthropic.com", content)
                self.assertNotIn("amazonaws.com", content)
                # Ensure no live private key headers
                self.assertNotIn("-----BEGIN RSA PRIVATE KEY-----", content)
                self.assertNotIn("-----BEGIN OPENSSH PRIVATE KEY-----", content)


if __name__ == "__main__":
    unittest.main()
