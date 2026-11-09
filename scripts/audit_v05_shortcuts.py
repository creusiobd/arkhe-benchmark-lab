"""Audit pre-outcome observations for trivial single-feature label shortcuts."""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Dict, List

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from contracts.ground_truth import TrajectoryGroundTruth
from contracts.observation import TrajectoryObservation


def load_jsonl(path: Path, model: Any) -> List[Any]:
    with path.open("r", encoding="utf-8") as handle:
        return [model.model_validate_json(line) for line in handle if line.strip()]


def combined_text(trajectory: TrajectoryObservation, steps: int = 4) -> str:
    fields: List[str] = []
    for step in trajectory.steps[:steps]:
        fields.extend([
            step.mission.current_instruction,
            step.action.tool_name,
            step.action.target_resource,
            step.result.status,
            step.result.raw_observation,
        ])
    return " ".join(fields).lower()


def feature_table() -> Dict[str, Callable[[TrajectoryObservation], bool]]:
    return {
        "mission_instruction_changed": lambda item: any(
            step.mission.current_instruction != step.mission.original_mission for step in item.steps[:4]
        ),
        "containment_status": lambda item: any(
            step.result.status.upper() in {"BLOCKED", "DENIED", "CONTAINED", "WARNED"}
            for step in item.steps[:4]
        ),
        "external_or_untrusted_terms": lambda item: bool(re.search(r"external|untrusted|third-party", combined_text(item))),
        "sensitive_asset_terms": lambda item: bool(re.search(r"secret|token|credential|environment", combined_text(item))),
        "capability_terms": lambda item: bool(re.search(r"capability|tool|shell|delegate", combined_text(item))),
        "failed_status": lambda item: any(step.result.status.upper() == "FAILED" for step in item.steps[:4]),
        "forbidden_target_before_step_4": lambda item: any(
            any(pattern.rstrip("*").lower() in step.action.target_resource.lower() for pattern in step.boundary.forbidden_targets)
            for step in item.steps[:4]
        ),
    }


def audit(dataset_dir: Path, fail_threshold: float = 0.95) -> Dict[str, Any]:
    observations = load_jsonl(dataset_dir / "observations.jsonl", TrajectoryObservation)
    truths = load_jsonl(dataset_dir / "ground_truth" / "v0.5_labels.jsonl", TrajectoryGroundTruth)
    truth_by_id = {item.trajectory_id: item for item in truths}
    rows = []
    y = [truth_by_id[item.trajectory_id].ground_truth_class.value == "violation" for item in observations]
    majority_accuracy = max(sum(y), len(y) - sum(y)) / len(y)

    for name, function in feature_table().items():
        values = [bool(function(item)) for item in observations]
        direct = sum(pred == actual for pred, actual in zip(values, y)) / len(y)
        inverse = sum((not pred) == actual for pred, actual in zip(values, y)) / len(y)
        best = max(direct, inverse)
        rows.append({
            "feature": name,
            "present": sum(values),
            "best_single_feature_accuracy": round(best, 4),
            "orientation": "direct" if direct >= inverse else "inverse",
            "fails": best >= fail_threshold,
        })

    label_words = re.compile(r"\b(benign|near[_ -]?violation|violation)\b", re.IGNORECASE)
    leaked_ids = [item.trajectory_id for item in observations if label_words.search(combined_text(item, steps=5))]
    report = {
        "dataset": str(dataset_dir.relative_to(BASE_DIR) if dataset_dir.is_relative_to(BASE_DIR) else dataset_dir),
        "n": len(observations),
        "task_a_class_counts": dict(Counter("positive" if value else "negative" for value in y)),
        "majority_accuracy": round(majority_accuracy, 4),
        "fail_threshold": fail_threshold,
        "label_word_leakage_count": len(leaked_ids),
        "features": rows,
        "passed": not leaked_ids and not any(row["fails"] for row in rows),
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="datasets/v0.5_hard")
    parser.add_argument("--output", default="reports/v0.5_shortcut_audit.json")
    parser.add_argument("--fail-threshold", type=float, default=0.95)
    args = parser.parse_args()
    dataset = Path(args.dataset)
    output = Path(args.output)
    if not dataset.is_absolute():
        dataset = BASE_DIR / dataset
    if not output.is_absolute():
        output = BASE_DIR / output
    report = audit(dataset, args.fail_threshold)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
