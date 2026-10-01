"""
Freeze Sample for OpenAI Live Pilot v0.4
=========================================
Extracts and documents the 50 frozen trajectories from datasets/v0.4_hard/
Recording exact opaque IDs, step counts, input SHA-256 hashes, and distribution.
"""

import os
import sys
import json
import hashlib
from typing import Dict, List, Any

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from contracts.observation import TrajectoryObservation
from contracts.ground_truth import TrajectoryGroundTruth


def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def main():
    output_dir = os.path.join(BASE_DIR, "results", "openai_pilot_v0.4")
    os.makedirs(output_dir, exist_ok=True)
    manifest_path = os.path.join(output_dir, "sample_freeze_manifest.json")

    splits = ["development", "validation", "test"]
    file_hashes = {}
    trajectories_catalog = []
    distribution = {
        "by_split": {},
        "by_family": {},
        "by_class": {},
        "total_trajectories": 0,
        "total_steps": 0
    }

    for split in splits:
        obs_file = os.path.join(BASE_DIR, "datasets", "v0.4_hard", "observations", f"{split}.jsonl")
        gt_file = os.path.join(BASE_DIR, "datasets", "v0.4_hard", "ground_truth", f"{split}_labels.jsonl")

        obs_hash = compute_sha256(obs_file)
        gt_hash = compute_sha256(gt_file)
        file_hashes[f"observations/{split}.jsonl"] = obs_hash
        file_hashes[f"ground_truth/{split}_labels.jsonl"] = gt_hash

        # Load observations
        obs_list = []
        with open(obs_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    obs_list.append(TrajectoryObservation.model_validate_json(line))

        # Load ground truth for metadata documentation only
        gt_map = {}
        with open(gt_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    gt = TrajectoryGroundTruth.model_validate_json(line)
                    gt_map[gt.trajectory_id] = gt

        distribution["by_split"][split] = len(obs_list)

        for obs in obs_list:
            gt = gt_map[obs.trajectory_id]
            fam = gt.scenario_family.value if hasattr(gt.scenario_family, "value") else str(gt.scenario_family)
            cls_name = gt.ground_truth_class.value if hasattr(gt.ground_truth_class, "value") else str(gt.ground_truth_class)

            distribution["by_family"][fam] = distribution["by_family"].get(fam, 0) + 1
            distribution["by_class"][cls_name] = distribution["by_class"].get(cls_name, 0) + 1
            distribution["total_trajectories"] += 1
            distribution["total_steps"] += len(obs.steps)

            trajectories_catalog.append({
                "trajectory_id": obs.trajectory_id,
                "split": split,
                "step_count": len(obs.steps),
                "family": fam,
                "class": cls_name,
                "hard_category": "stealth_pressure_or_adversarial_framing"
            })

    freeze_doc = {
        "manifest_version": "1.0.0",
        "dataset_version": "v0.4_hard",
        "freeze_date_utc": "2026-09-30T22:00:00Z",
        "selection_criteria": "All 50 structurally disjoint hard trajectories from v0.4_hard across development, validation, and test partitions",
        "dataset_file_hashes": file_hashes,
        "sample_distribution": distribution,
        "frozen_trajectories": trajectories_catalog
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(freeze_doc, f, indent=2)

    print(f"[OK] Sample freeze manifest generated successfully: {manifest_path}")
    print(f"     Total trajectories: {distribution['total_trajectories']} | Total steps: {distribution['total_steps']}")
    print(f"     Splits: {distribution['by_split']}")
    print(f"     Families: {distribution['by_family']}")
    print(f"     Classes: {distribution['by_class']}")


if __name__ == "__main__":
    main()
