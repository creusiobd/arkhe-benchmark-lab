"""
ARKHÉ Agent Boundary Defense Benchmark — Deterministic Reproduction Verifier
=============================================================================
Executes a dual-generation verification test in isolated temporary directories.
Validates that:
1. Environment, seed, configuration, and dependencies are valid.
2. Two independent generator executions produce 100% bitwise identical dataset files and SHA-256 hashes.
3. Excludes intentionally variable runtime execution fields (timestamps, duration) from hash comparisons.
4. Optionally validates that the tracked active dataset files (datasets/v0.4_hard) match the generator.
5. Returns exit code 0 on perfect match, non-zero on any divergence.
"""

import os
import sys
import json
import yaml
import hashlib
import platform
import argparse
import tempfile
from typing import Dict, List, Tuple, Any, Optional

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from scripts.generate_hard_dataset import (
    generate_hard_dataset, compute_file_sha256, DEFAULT_RANDOM_SEED
)

DATASET_FILES = [
    "observations/development.jsonl",
    "observations/validation.jsonl",
    "observations/test.jsonl",
    "ground_truth/development_labels.jsonl",
    "ground_truth/validation_labels.jsonl",
    "ground_truth/test_labels.jsonl",
    "templates/templates_catalog.json",
    "dataset_card.md",
    "LICENSE",
]


def validate_environment_and_inputs(config_path: str, seed: int) -> Dict[str, Any]:
    """Step 1: Validates runtime environment, seed, config, and required dependencies."""
    print("--- [1/5] Validating Environment, Dependencies, and Configuration ---")
    
    # 1. Python version check
    py_ver = sys.version_info
    if py_ver < (3, 10):
        raise RuntimeError(f"Python 3.10+ required. Found {py_ver.major}.{py_ver.minor}.{py_ver.micro}")
    print(f"• Python version: {platform.python_version()} ({platform.python_implementation()}) [OK]")

    # 2. Config existence
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    print(f"• Config file: {config_path} [OK]")

    # 3. Seed validation
    if not isinstance(seed, int) or seed < 0:
        raise ValueError(f"Invalid random seed: {seed}. Must be a non-negative integer.")
    print(f"• Random seed: {seed} [OK]")

    # 4. Core dependency checks
    missing_deps = []
    for mod in ["pydantic", "yaml"]:
        try:
            __import__(mod)
        except ImportError:
            missing_deps.append(mod)
    if missing_deps:
        raise ImportError(f"Required dependencies missing: {missing_deps}")
    print(f"• Essential dependencies: pydantic, pyyaml [OK]\n")

    return cfg


def hash_directory_files(directory: str, file_list: List[str]) -> Dict[str, str]:
    """Computes SHA-256 hashes for all expected files in a directory."""
    hashes = {}
    for rel_path in file_list:
        full_path = os.path.join(directory, rel_path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Expected generated file missing: {full_path}")
        hashes[rel_path] = compute_file_sha256(full_path)
    return hashes


def run_deterministic_verification(
    config_path: str,
    seed: int,
    output_dir_1: Optional[str] = None,
    output_dir_2: Optional[str] = None,
    check_tracked: bool = False
) -> int:
    """Executes the dual-run determinism verification protocol."""
    print(f"\n================================================================================")
    print(f"      ARKHÉ AGENT BENCHMARK — DETERMINISTIC REPRODUCTION VERIFIER")
    print(f"================================================================================\n")

    validate_environment_and_inputs(config_path, seed)

    # Use explicit directories or create temporary ones
    temp_dir_1_obj = None
    temp_dir_2_obj = None

    try:
        if output_dir_1:
            dir1 = output_dir_1
            os.makedirs(dir1, exist_ok=True)
        else:
            temp_dir_1_obj = tempfile.TemporaryDirectory()
            dir1 = temp_dir_1_obj.name

        if output_dir_2:
            dir2 = output_dir_2
            os.makedirs(dir2, exist_ok=True)
        else:
            temp_dir_2_obj = tempfile.TemporaryDirectory()
            dir2 = temp_dir_2_obj.name

        # Step 2: First generation
        print("--- [2/5] Executing Generation Run 1 (Isolated Target 1) ---")
        m1 = generate_hard_dataset(
            output_dir=dir1,
            seed=seed,
            config_path=config_path,
            emit_report=False
        )

        # Step 3: Second generation with identical inputs
        print("\n--- [3/5] Executing Generation Run 2 (Isolated Target 2) ---")
        m2 = generate_hard_dataset(
            output_dir=dir2,
            seed=seed,
            config_path=config_path,
            emit_report=False
        )

        # Step 4: Compute and compare hashes
        print("\n--- [4/5] Computing SHA-256 Hashes and Verifying Bitwise Equality ---")
        hashes1 = hash_directory_files(dir1, DATASET_FILES)
        hashes2 = hash_directory_files(dir2, DATASET_FILES)

        divergences: List[Tuple[str, str, str]] = []

        print(f"\n{'Artifact Path':<45} | {'Run 1 SHA-256 (first 16)':<24} | {'Run 2 SHA-256 (first 16)':<24} | Status")
        print("-" * 110)

        for rel_path in DATASET_FILES:
            h1 = hashes1[rel_path]
            h2 = hashes2[rel_path]
            is_match = (h1 == h2)
            status_str = "[MATCH]" if is_match else "[DIVERGENCE]"
            print(f"{rel_path:<45} | {h1[:16]}...           | {h2[:16]}...           | {status_str}")

            if not is_match:
                divergences.append((rel_path, h1, h2))

        # Compare manifest deterministic metadata (excluding variable runtime metrics)
        det_meta_1 = m1.get("deterministic_metadata", {})
        det_meta_2 = m2.get("deterministic_metadata", {})
        manifest_meta_match = (det_meta_1 == det_meta_2)

        print("-" * 110)
        print(f"{'Manifest deterministic_metadata':<45} | {'(exact dict match)':<24} | {'(exact dict match)':<24} | {'[MATCH]' if manifest_meta_match else '[DIVERGENCE]'}")

        if not manifest_meta_match:
            divergences.append(("generation_manifest.json (deterministic_metadata)", str(det_meta_1), str(det_meta_2)))

        # Step 5: Optional check against tracked repo dataset
        if check_tracked:
            print("\n--- [5/5] Validating Against Tracked Repository Dataset (datasets/v0.4_hard) ---")
            tracked_dir = os.path.join(BASE_DIR, "datasets", "v0.4_hard")
            tracked_hashes = hash_directory_files(tracked_dir, DATASET_FILES)

            tracked_divergences = []
            for rel_path in DATASET_FILES:
                h_gen = hashes1[rel_path]
                h_tracked = tracked_hashes[rel_path]
                if h_gen != h_tracked:
                    tracked_divergences.append((rel_path, h_gen, h_tracked))
                    print(f"❌ Tracked divergence: {rel_path} (Gen: {h_gen[:12]} vs Tracked: {h_tracked[:12]})")
                else:
                    print(f"✓ Tracked verified: {rel_path} ({h_gen[:16]}...)")

            if tracked_divergences:
                print(f"\n❌ ERROR: {len(tracked_divergences)} files in datasets/v0.4_hard diverge from the deterministic generator!")
                return 1
            else:
                print("\n✓ SUCCESS: Tracked repository dataset in datasets/v0.4_hard matches deterministic generator 100%!")

        if divergences:
            print(f"\n❌ DETERMINISM FAILURE: {len(divergences)} artifacts diverged between run 1 and run 2!")
            for path, h1, h2 in divergences:
                print(f"  • {path}: Run1={h1[:16]} != Run2={h2[:16]}")
            return 1

        print("\n" + "=" * 110)
        print("✓ SUCCESS: 100% Deterministic Dataset Reproduction Verified across all 9 dataset files.")
        print("           Manifest provenance metadata matches exactly.")
        print("=" * 110 + "\n")
        return 0

    finally:
        if temp_dir_1_obj:
            temp_dir_1_obj.cleanup()
        if temp_dir_2_obj:
            temp_dir_2_obj.cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ARKHÉ Deterministic Dataset Reproduction Verifier")
    parser.add_argument("--config", default="configs/hard_candidate_v0.4.yaml", help="Path to config YAML file")
    parser.add_argument("--seed", type=int, default=DEFAULT_RANDOM_SEED, help="Random seed for generation")
    parser.add_argument("--output-dir-1", default=None, help="Optional explicit directory for Run 1")
    parser.add_argument("--output-dir-2", default=None, help="Optional explicit directory for Run 2")
    parser.add_argument("--check-tracked", action="store_true", help="Also verify that tracked datasets/v0.4_hard matches")
    args = parser.parse_args()

    cfg_file = args.config
    if not os.path.isabs(cfg_file):
        cfg_file = os.path.join(BASE_DIR, cfg_file)

    exit_code = run_deterministic_verification(
        config_path=cfg_file,
        seed=args.seed,
        output_dir_1=args.output_dir_1,
        output_dir_2=args.output_dir_2,
        check_tracked=args.check_tracked
    )
    sys.exit(exit_code)
