"""Freeze protocol, dataset, scoring code, and split definitions by SHA-256."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Dict

BASE_DIR = Path(__file__).resolve().parents[1]

FROZEN_FILES = [
    "configs/evaluation_protocol_v0.5.yaml",
    "contracts/evaluation_protocol.py",
    "contracts/observation.py",
    "contracts/ground_truth.py",
    "calibration/select_threshold.py",
    "detectors/base.py",
    "detectors/deterministic_event.py",
    "detectors/semantic_event.py",
    "detectors/arkhe_trajectory.py",
    "detectors/clients/openai_semantic_client.py",
    "harness/run_v05_folds.py",
    "evaluator/evaluate_v05.py",
    "datasets/v0.5_hard/observations.jsonl",
    "datasets/v0.5_hard/ground_truth/v0.5_labels.jsonl",
    "datasets/v0.5_hard/split_manifest.json",
    "datasets/v0.5_hard/generation_manifest.json",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_state() -> Dict[str, Any]:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=BASE_DIR, check=True, capture_output=True, text=True).stdout.strip()
    status = subprocess.run(["git", "status", "--porcelain"], cwd=BASE_DIR, check=True, capture_output=True, text=True).stdout.splitlines()
    return {"source_commit": commit, "worktree_dirty": bool(status), "dirty_paths": status}


def create_freeze(output: Path) -> Dict[str, Any]:
    missing = [path for path in FROZEN_FILES if not (BASE_DIR / path).exists()]
    if missing:
        raise FileNotFoundError(f"Cannot freeze; missing files: {missing}")
    files = {path: sha256_file(BASE_DIR / path) for path in FROZEN_FILES}
    canonical = json.dumps(files, sort_keys=True, separators=(",", ":"))
    freeze_id = "freeze_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]
    freeze = {
        "freeze_id": freeze_id,
        "protocol_id": "arkhe-prospective-v0.5",
        "claim_eligibility": "reproducibility_only",
        "eligibility_reason": "v0.5 test-family outputs were inspected during development before this freeze",
        **git_state(),
        "files": files,
        "rules": {
            "threshold_source": "validation_only",
            "test_unit": "held_out_family",
            "repetition_1": "primary",
            "repetition_2": "repeatability_only",
            "confirmatory_claims_allowed": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(freeze, indent=2) + "\n", encoding="utf-8")
    return freeze


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="freezes/v0.5_freeze.json")
    args = parser.parse_args()
    output = Path(args.output)
    if not output.is_absolute(): output = BASE_DIR / output
    print(json.dumps(create_freeze(output), indent=2))


if __name__ == "__main__":
    main()
